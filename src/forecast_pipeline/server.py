"""
FastAPI server for the Revenue Forecast Pipeline.

Exposes endpoints to:
- Fetch SEC financial data for a ticker
- Generate revenue forecasts
- Get forecast with a single API call
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
import pandas as pd
import logging

from forecast_pipeline.data_ingest import fetch_financial_features
from forecast_pipeline.retrain_model import forecast_revenue, ArimaForecastStrategy

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Revenue Forecast Pipeline API",
    description="SEC data ingestion and ARIMA/SARIMAX forecasting service",
    version="1.0.0"
)


# Request/Response models
class ForecastRequest(BaseModel):
    """Request model for forecast endpoint."""
    ticker: str = Query(..., description="Stock ticker symbol (e.g., AAPL)")
    is_quarterly: bool = Query(False, description="Use quarterly seasonality in forecast")


class ForecastResponse(BaseModel):
    """Response model for forecast endpoint."""
    ticker: str
    forecast_value: float
    data_points: int
    is_quarterly: bool
    message: str


class FinancialDataResponse(BaseModel):
    """Response model for financial data endpoint."""
    ticker: str
    company_name: Optional[str]
    revenue_data: Dict[str, float]
    data_points: int


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/predict", response_model=ForecastResponse, tags=["Forecasting"])
async def predict_forecast(request: ForecastRequest):
    """
    Generate a 1-step-ahead revenue forecast for a given ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., AAPL)
        is_quarterly: Whether to apply quarterly seasonality
    
    Returns:
        Forecast value and metadata
    """
    try:
        logger.info(f"Fetching financial data for ticker: {request.ticker}")
        
        financial_data = fetch_financial_features(request.ticker)
        
        if financial_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No financial data found for ticker: {request.ticker}"
            )
        
        financial_data = financial_data.dropna(subset=["Total Revenue"])
        
        if len(financial_data) < 6:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient data points ({len(financial_data)}). Minimum 6 required for forecasting."
            )
        
        revenue_dict = dict(
            zip(
                financial_data["Fiscal Period"].astype(str),
                financial_data["Total Revenue"].astype(float)
            )
        )
        
        logger.info(f"Generating forecast with {len(revenue_dict)} data points")
        strategy = ArimaForecastStrategy()
        forecast_value = forecast_revenue(revenue_dict, request.is_quarterly, strategy)
        
        return ForecastResponse(
            ticker=request.ticker,
            forecast_value=forecast_value,
            data_points=len(revenue_dict),
            is_quarterly=request.is_quarterly,
            message=f"1-step-ahead revenue forecast generated using {len(revenue_dict)} historical periods"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating forecast: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")


@app.get("/", response_model=FinancialDataResponse, tags=["Data"])
async def read_financial_history(ticker: str = Query(..., description="Stock ticker symbol (e.g., AAPL)")):
    """
    Fetch historical financial data for a given ticker.
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Dictionary of fiscal periods and revenue values
    """
    try:
        logger.info(f"Fetching financial data for ticker: {ticker}")
        
        financial_data = fetch_financial_features(ticker)
        
        if financial_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No financial data found for ticker: {ticker}"
            )
        
        financial_data = financial_data.dropna(subset=["Total Revenue"])
        
        revenue_dict = dict(
            zip(
                financial_data["Fiscal Period"].astype(str),
                financial_data["Total Revenue"].astype(float)
            )
        )
        
        return FinancialDataResponse(
            ticker=ticker,
            company_name=financial_data.get("Company Name", ticker),
            revenue_data=revenue_dict,
            data_points=len(revenue_dict)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching financial data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Data fetch failed: {str(e)}")


@app.get("/info", tags=["Info"])
async def root():
    """Root info endpoint with API documentation links."""
    return {
        "name": "Revenue Forecast Pipeline API",
        "version": "1.0.0",
        "description": "SEC data ingestion and ARIMA/SARIMAX forecasting service",
        "endpoints": {
            "GET /?ticker=...": "Fetch historical financial data",
            "POST /predict": "Generate 1-step-ahead revenue forecast",
            "GET /docs": "Interactive API documentation (Swagger UI)",
            "GET /redoc": "Alternative API documentation (ReDoc)",
            "GET /health": "Health check"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
