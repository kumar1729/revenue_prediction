# My Forecast Library
A custom library for automated time-series financial modeling.


Automated SEC Data Ingestion & Time-Series Forecasting PipelineAn automated, data-driven machine learning pipeline that dynamically interfaces with the United States Securities and Exchange Commission (SEC) EDGAR API system to extract corporate financial history and generate 1-step-ahead revenue forecasts.The project uses a modular design pattern, leveraging Abstract Base Classes (abc) to allow seamless swapping of mathematical forecasting engines.📋 Table of ContentsArchitecture OverviewProject

 Directory StructureData Pipeline MechanicsInstallation & SetupUsage InstructionsCore ML Forecasting Engine🏗️ Architecture OverviewThe application is structured into two main decoupled automation layers:data_ingest.py (Ingestion Layer): Converts user-supplied ticker strings into a unique 10-digit Central Index Key (CIK), handles secure, rate-compliant compression handshakes with the SEC servers, maps erratic accounting taxonomy shifts, and generates a structured chronological time-series file (.csv).retrain_model.py (ML Engine Layer): Ingests the tabular dataset, dynamically checks chronological periodicity constraints, and invokes an Autoregressive Integrated Moving Average (ARIMA/SARIMAX) statistical framework to predict upcoming corporate financial performance.[Terminal Input: --ticker] ➔ [SEC Dynamic CIK Lookup] ➔ [XBRL Company Facts API] 
 
 
                                                                  │
[Downstream Retraining Engine] 🔀 [ARIMA/SARIMAX Model] 🗃️ [Chronological CSV Data Matrix]


📁 Project Directory Structuretextforecast_pipeline/


│
├── .gitignore                      # Prevents local data leaks and cache tracking


├── requirements.txt                # Third-party dependency definitions


├── README.md                       # Complete project production blueprint


│
├── data_ingest.py                  # SEC real-time ingestion layer


└── retrain_model.py                # Time-series modeling & forecasting engine


 Data Pipeline MechanicsCorporate entity accounting frameworks change frequently across decades. This pipeline implements several advanced data normalization rules to handle those changes:Taxonomy Fallback Chains: Resolves historical accounting reclassifications by scanning fallback arrays (e.g., matching RevenueFromContractWithCustomerExcludingAssessedTax, SalesRevenueNet, or Revenues).Frame Interval Separation: Inspects the SEC structural frame attributes to map 10-Q filings strictly to 3-month windows (CY2025Q1) and 10-K filings strictly to 12-month frames (CY2025), preventing data overlap.SEC Security Compliant Headers: Employs mandatory global tracking declarations and explicitly enforces gzip, deflate encryption parameters to bypass SEC API firewall connection blocks.
 
 
 Installation & SetupEnsure you have a Python environment installed (compatible with Python >= 3.8).Clone the project locally from your GitHub profile:bashgit clone https://github.com
 
 
cd revenue_prediction


Install the necessary third-party analytical dependency packages:bashpip install -r requirements.txt
Usage InstructionsThe pipeline runs entirely via a single terminal interface command flag.Run Ingestion & Automatic RetrainingExecute data_ingest.py and supply any valid U.S. stock ticker symbol via the --ticker argument:bashpython3 data_ingest.py --ticker AAPL\


bash. python3 data_ingest.py --ticker NVDA


What Happens Behind the Scenes:The script downloads the data and writes a local, unmutated dataset file alongside your scripts (AAPL_historical_financials.csv).data_ingest.py automatically checks for the existence of retrain_model.py and executes it downstream via a secure sub-process call.The training engine isolates missing fields, structures an autowrapped dictionary matrix, determines data seasonality, and outputs a prediction directly to your shell window.Independent Model EvaluationIf you already have a generated data file and want to retrain or evaluate the statistical model directly, run:bashpython3 retrain_model.py --data_path AAPL_historical_financials.csv


Core ML Forecasting EngineThe prediction pipeline uses Abstract Base Classes (abc) to separate the forecasting logic from the data handling.The Interface Strategy (ForecastStrategy): An abstract base class that forces all forecasting strategies to implement a standard .forecast(rev_dict, is_quarterly) execution signature. This design makes the pipeline completely modular; you can plug in a deep learning strategy (like an LSTM or Transformer) later without touching any data-handling code.The Default Model (ArimaForecastStrategy): Iterates through multiple parametric candidates, dynamically evaluating Akaike Information Criterion (AIC) scoring matrix properties to fit the optimal order combination:For small arrays (< 8 points): Compares ARIMA(0,1,1) and ARIMA(1,1,0).For larger arrays (>= 8 points): Compares ARIMA(1,1,1), ARIMA(1,1,0), and ARIMA(0,1,1).For quarterly operations containing substantial historical footprints (>= 12 quarters): Evaluates a full SARIMAX model with seasonal orders matching annual bounds (1, 0, 1, 4).