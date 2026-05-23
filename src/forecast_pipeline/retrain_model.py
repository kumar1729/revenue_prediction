"""
retrain_model.py

Implements a strategy-based design for forecasting revenue data.
Accepts an SEC historical feature matrix CSV from a pipeline run, parses the 
historical landscape, and computes the 1-step-ahead forecasted prediction value.
"""

import abc
import argparse
import os
import warnings
import numpy as np
import pandas as pd

# Fallback utilities to make the script self-contained if helper files are absent
def parse_period_label(label: str) -> str:
    """Helper to ensure alphanumeric period structures sort cleanly."""
    return str(label)

class SimpleLogger:
    """Minimal self-contained fallback logging layer."""
    def warning(self, msg, *args):
        print(f"[WARNING] {msg % args if args else msg}")
    def info(self, msg, *args):
        print(f"[INFO] {msg % args if args else msg}")

logger = SimpleLogger()

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.arima.model import ARIMA
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

MIN_DATA_POINTS = 6
MIN_SEASONAL_DATA_POINTS = 12


class ForecastStrategy(abc.ABC):
    """
    Abstract base class for forecasting strategies.

    Each strategy must implement the .forecast(rev_dict, is_quarterly) method
    and return a single float representing the 1-step-ahead forecast.
    """

    @abc.abstractmethod
    def forecast(self, rev_dict: dict, is_quarterly: bool = False) -> float:
        """
        Compute a 1-step revenue forecast from rev_dict,
        optionally considering is_quarterly for seasonal dynamics.
        """


class ArimaForecastStrategy(ForecastStrategy):
    """
    Default ARIMA-based forecasting strategy.

    - Uses statsmodels ARIMA or SARIMAX for seasonal logic.
    - Requires >= MIN_DATA_POINTS or returns naive fallback.
    - Negative forecasts are preserved to surface declining trends.
    """

    def forecast(self, rev_dict: dict, is_quarterly: bool = False) -> float:
        sorted_periods = sorted(rev_dict.keys(), key=parse_period_label)
        series_vals = [float(rev_dict[p]) for p in sorted_periods]
        naive_fallback = series_vals[-1] if series_vals else 0.0

        if not HAS_STATSMODELS or len(rev_dict) < MIN_DATA_POINTS:
            logger.warning(
                "ArimaForecastStrategy: insufficient data (%d pts) or statsmodels missing => naive fallback=%.2f",
                len(rev_dict), naive_fallback,
            )
            return naive_fallback

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                warnings.filterwarnings("ignore", message=".*convergence.*")

                candidates = []
                if len(series_vals) < 8:
                    candidates = [
                        ARIMA(series_vals, order=(0, 1, 1)),
                        ARIMA(series_vals, order=(1, 1, 0)),
                    ]
                else:
                    candidates = [
                        ARIMA(series_vals, order=(1, 1, 1)),
                        ARIMA(series_vals, order=(1, 1, 0)),
                        ARIMA(series_vals, order=(0, 1, 1)),
                    ]
                    if is_quarterly and len(series_vals) >= MIN_SEASONAL_DATA_POINTS:
                        candidates.append(
                            SARIMAX(
                                series_vals,
                                order=(1, 1, 1),
                                seasonal_order=(1, 0, 1, 4),
                                trend='c',
                                enforce_stationarity=True,
                                enforce_invertibility=True,
                            )
                        )

                best_aic = float("inf")
                best_fit = None
                for cand in candidates:
                    try:
                        cand_fit = cand.fit()
                        if cand_fit.aic < best_aic:
                            best_aic = cand_fit.aic
                            best_fit = cand_fit
                    except Exception as exc:
                        pass  # Fail silently across weak tuning candidates

                if not best_fit:
                    logger.warning(
                        "ArimaForecastStrategy: no suitable model found => naive fallback=%.2f",
                        naive_fallback,
                    )
                    return naive_fallback

                forecast_arr = best_fit.forecast(steps=1)
                forecast_val = float(np.squeeze(forecast_arr))

                if not np.isfinite(forecast_val):
                    logger.warning(
                        "ArimaForecastStrategy: non-finite forecast (NaN/Inf) => naive fallback=%.2f",
                        naive_fallback,
                    )
                    return naive_fallback

                if forecast_val < 0.0:
                    logger.warning(
                        "ArimaForecastStrategy: negative forecast=%.2f (declining revenue trend)",
                        forecast_val,
                    )
                return forecast_val

        except Exception as exc:
            logger.warning(
                "ArimaForecastStrategy: exception during forecast => %s => naive fallback=%.2f",
                exc, naive_fallback,
            )
            return naive_fallback


def forecast_revenue(
    rev_dict: dict,
    is_quarterly: bool = False,
    strategy: ForecastStrategy = None
) -> float:
    """Main entry point to forecast the next revenue value."""
    if strategy is None:
        strategy = ArimaForecastStrategy()
    return strategy.forecast(rev_dict, is_quarterly)


if __name__ == "__main__":
    # 1. Accept incoming data pipeline parameters from terminal run commands
    parser = argparse.ArgumentParser(description="Downstream Model Pipeline Engine Trainer")
    parser.add_argument(
        "--data_path", 
        type=str, 
        required=True, 
        help="Absolute or relative path to the generated SEC financial metrics CSV file."
    )
    args = parser.parse_args()

    # 2. Extract configuration matrices from data frame files safely
    if not os.path.exists(args.data_path):
        print(f"[Execution Error] Designated CSV feature matrix not found at path: {args.data_path}")
        exit(1)

    df = pd.read_csv(args.data_path)
    
    # Verify minimal pipeline column configurations
    required_cols = ["Fiscal Period", "Total Revenue", "Filing Form"]
    if not all(col in df.columns for col in required_cols):
        print(f"[Execution Error] Input file missing mandatory feature fields: {required_cols}")
        exit(1)

    # Drop blank revenue data arrays if any exist
    df.dropna(subset=["Total Revenue"], inplace=True)

    if df.empty:
        print("[Execution Error] Provided data framework contains zero usable revenue points.")
        exit(1)

    # 3. Shape historical rows cleanly into strategy dictionary matrices
    # { 'CY2024Q3': 94930000000.0 }
    revenue_dictionary = dict(zip(df["Fiscal Period"].astype(str), df["Total Revenue"].astype(float)))

    # Determine structural quarter flags by inspecting row frequencies
    contains_quarters = (df["Filing Form"] == "10-Q").any()

    print(f"\n--- Downstream ML Model Engine Initialized ---")
    print(f"Total Active Historical Steps Parsed: {len(revenue_dictionary)}")
    print(f"Detected Seasonal Step Type:          {'Quarterly (10-Q)' if contains_quarters else 'Annual (10-K)'}")

    # 4. Compute 1-Step-Ahead Time-Series Predictions
    predicted_next_revenue = forecast_revenue(revenue_dictionary, is_quarterly=contains_quarters)
    
    print(f"\n>>> NEXT PERIOD REVENUE PREDICTION RESULT: ${predicted_next_revenue:,.2f} USD <<<\n")

