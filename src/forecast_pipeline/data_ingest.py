import subprocess
import os
import urllib.parse
import pandas as pd
import requests


# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

csv_output_path = os.path.join(current_dir, "apple_historical_financials.csv")

# Build the paths to the downstream script and the output data target
script_path = os.path.join(current_dir, "retrain_model.py")
csv_output_path = os.path.join(current_dir, "apple_historical_financials.csv")

# 1. Define SEC-compliant headers (Mandatory identification + compression layers)
HEADERS = {
    "User-Agent": "KumarShubham/1.0 (rekhakshubham@gmail.com)",
    "Accept-Encoding": "gzip, deflate"
}

# Explicitly isolate the domain and CIK parameters
SEC_DOMAIN = "https://data.sec.gov"
APPLE_CIK = "AAPL"



def get_cik_from_ticker(ticker: str) -> str:
    """Dynamically converts a ticker symbol to a 10-digit SEC CIK string."""
    # Force uppercase formatting to avoid text mismatch
    target_ticker = ticker.upper().strip()
    ticker_url = "https://www.sec.gov/files/company_tickers.json"

    try:
        response = requests.get(ticker_url, headers=HEADERS)
        response.raise_for_status()
        ticker_data = response.json()

        # Iterate through SEC dictionary to map ticker -> CIK
        for entry in ticker_data.values():
            # Standardize registry comparison text casing
            if str(entry["ticker"]).upper() == target_ticker:
                return str(entry["cik_str"]).zfill(10)

        print(f"Error: Ticker '{target_ticker}' not found in SEC registries.")
        return None
    except requests.exceptions.RequestException as err:
        print(f"Ticker mapping failed: {err}")
        return None


def fetch_financial_features(ticker: str) -> pd.DataFrame:
    """Safely constructs endpoints using URL standard libraries and sweeps

    ALL historical fiscal periods into a structured time-series matrix.
    """
    cik = get_cik_from_ticker(ticker)
    if not cik:
        return pd.DataFrame()
        
    clean_cik = str(cik).zfill(10)

    meta_path = f"submissions/CIK{clean_cik}.json"
    facts_path = f"api/xbrl/companyfacts/CIK{clean_cik}.json"

    metadata_url = urllib.parse.urljoin(f"{SEC_DOMAIN}/", meta_path)
    facts_url = urllib.parse.urljoin(f"{SEC_DOMAIN}/", facts_path)

    print("--- 1. Verification of Safe Pipeline URLs ---")
    print(f"Target Meta Domain:  {metadata_url}")
    print(f"Target Facts Domain: {facts_url}\n")

    try:
        # Step A: Query Metadata Endpoint to capture valid filing reference logs
        meta_response = requests.get(metadata_url, headers=HEADERS)
        meta_response.raise_for_status()
        meta_data = meta_response.json()

        company_name = meta_data.get("name", "Target Entity")
        recent_filings = meta_data["filings"]["recent"]
        history_base_df = pd.DataFrame(recent_filings)

        # Retain both 10-Q and 10-K to span across all fiscal periods
        target_filings = history_base_df[history_base_df["form"].isin(["10-Q", "10-K"])].copy()
        
        print("--- 2. SEC EDGAR History Matrix Discovered ---")
        print(f"Company Profile:  {company_name}")
        print(f"Total Tracking Records Found: {len(target_filings)}\n")

        # Step B: Query Accounting Facts Ledger
        facts_response = requests.get(facts_url, headers=HEADERS)
        facts_response.raise_for_status()
        facts_data = facts_response.json()

        # Match structural business features to fallback US-GAAP taxonomy arrays
        target_metrics = {
            "Total Revenue": [
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
                "RevenueFromContractWithCustomerNetOfTax",
            ],
            "Net Income": ["NetIncomeLoss"],
            "Total Assets": ["Assets"],
        }

        gaap_data = facts_data.get("facts", {}).get("us-gaap", {})

        # Map timeline tracker dictionary keyed by Accession ID
        time_series_matrix = {}
        for _, row in target_filings.iterrows():
            accn = row["accessionNumber"]
            time_series_matrix[accn] = {
                "Filing Form": row["form"],
                "Filing Date": row["filingDate"],
                "Period End Date": row["reportDate"],
                "Fiscal Period": None,
                "Total Revenue": None,
                "Net Income": None,
                "Total Assets": None,
            }

        # Step C: Populate tracking columns through the history ledger
        for label, xbrl_tags in target_metrics.items():
            for xbrl_tag in xbrl_tags:
                if xbrl_tag not in gaap_data:
                    continue

                currency_unit = list(gaap_data[xbrl_tag]["units"].keys())[0]
                data_points = gaap_data[xbrl_tag]["units"][currency_unit]

                for frame in data_points:
                    point_accn = frame.get("accn")
                    
                    if point_accn in time_series_matrix:
                        frame_label = frame.get("frame")
                        form_type = time_series_matrix[point_accn]["Filing Form"]

                        # Ensure 10-Q maps to short quarters and 10-K maps to full years
                        if form_type == "10-Q" and (frame_label and "Q" not in frame_label):
                            continue
                        if form_type == "10-K" and (frame_label and "Q" in frame_label):
                            continue

                        # Extract value if placeholder slot is empty
                        if time_series_matrix[point_accn][label] is None:
                            time_series_matrix[point_accn][label] = frame.get("val")
                            if frame_label:
                                time_series_matrix[point_accn]["Fiscal Period"] = frame_label
                
        # Step D: Flatten matrix down to chronological DataFrame
        final_df = pd.DataFrame.from_dict(time_series_matrix, orient="index")
        final_df.dropna(subset=["Total Revenue", "Net Income", "Total Assets"], how="all", inplace=True)

        # Standardize dates and apply strict oldest-to-newest ordering
        final_df["Period End Date"] = pd.to_datetime(final_df["Period End Date"])
        final_df["Filing Date"] = pd.to_datetime(final_df["Filing Date"])
        final_df["Fiscal Period"] = final_df["Fiscal Period"].fillna(final_df["Filing Form"])
        
        final_df.sort_values(by="Period End Date", ascending=True, inplace=True)
        final_df.reset_index(inplace=True)
        final_df.rename(columns={"index": "Accession Tag"}, inplace=True)

        return final_df

    except requests.exceptions.RequestException as network_err:
        print(f"Pipeline Connection Halted: {network_err}")
        return pd.DataFrame()


if __name__ == "__main__":
    # Execute clean comprehensive extraction run
    financial_df = fetch_financial_features(APPLE_CIK)

    if not financial_df.empty:
        print("--- 3. Extracted Historical Features Matrix ---")
        print(financial_df.to_string(index=False))
        
        # EXPORT LAYER: Save matrix as a clean CSV file (without index columns)
        financial_df.to_csv(csv_output_path, index=False)
        print(f"\n[Success] Final matrix saved locally: {csv_output_path}")
        
        # DOWNSTREAM TRIGGER: Automatically pass the generated CSV to the retraining loop
        if os.path.exists(script_path):
            print(f"Initiating pipeline downstream retraining: {script_path}...")
            subprocess.run(["python3", script_path, "--data_path", csv_output_path])
        else:
            print(f"\n[Pipeline Notice] '{script_path}' not found. Retraining execution skipped.")
    else:
        print("\n[Execution Error] Output is empty. CSV export aborted.")
        print("If URL is verified, confirm local VPN or Firewall rules.")
