"""
Dashboard module for displaying and comparing model predictions with real data.
Visualizes the last two predictions and actual data for model evaluation.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional


class DashboardGenerator:
    """Generate interactive dashboards for model prediction evaluation."""
    
    def __init__(self, output_dir: str = "dashboards"):
        """
        Initialize dashboard generator.
        
        Args:
            output_dir: Directory to save dashboard HTML files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_predictions(self, prediction_file: str) -> pd.DataFrame:
        """
        Load prediction data from file.
        
        Args:
            prediction_file: Path to CSV file containing predictions
            
        Returns:
            DataFrame with prediction data
        """
        return pd.read_csv(prediction_file, parse_dates=['date'])
    
    def load_actual_data(self, actual_file: str) -> pd.DataFrame:
        """
        Load actual revenue data.
        
        Args:
            actual_file: Path to CSV file containing actual revenue data
            
        Returns:
            DataFrame with actual data
        """
        return pd.read_csv(actual_file, parse_dates=['date'])
    
    def get_latest_two_predictions(self, predictions_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract the two most recent prediction runs.
        
        Assumes predictions_df has a 'model_version' or 'run_date' column
        to identify different prediction runs.
        
        Args:
            predictions_df: DataFrame containing all predictions
            
        Returns:
            Tuple of (latest_prediction_df, second_latest_prediction_df)
        """
        # Group by model version or run date to get unique prediction runs
        if 'model_version' in predictions_df.columns:
            versions = predictions_df['model_version'].unique()
            latest_versions = sorted(versions)[-2:] if len(versions) >= 2 else sorted(versions)
            
            if len(latest_versions) == 2:
                pred_latest = predictions_df[predictions_df['model_version'] == latest_versions[-1]].copy()
                pred_second = predictions_df[predictions_df['model_version'] == latest_versions[-2]].copy()
            else:
                pred_latest = predictions_df[predictions_df['model_version'] == latest_versions[-1]].copy()
                pred_second = pd.DataFrame()
        else:
            # Alternative: use run_date if available
            if 'run_date' in predictions_df.columns:
                run_dates = predictions_df['run_date'].unique()
                latest_dates = sorted(run_dates)[-2:] if len(run_dates) >= 2 else sorted(run_dates)
                
                if len(latest_dates) == 2:
                    pred_latest = predictions_df[predictions_df['run_date'] == latest_dates[-1]].copy()
                    pred_second = predictions_df[predictions_df['run_date'] == latest_dates[-2]].copy()
                else:
                    pred_latest = predictions_df[predictions_df['run_date'] == latest_dates[-1]].copy()
                    pred_second = pd.DataFrame()
            else:
                raise ValueError("predictions_df must contain 'model_version' or 'run_date' column")
        
        return pred_latest, pred_second
    
    def create_comparison_chart(
        self,
        actual_data: pd.DataFrame,
        pred_latest: pd.DataFrame,
        pred_second: pd.DataFrame,
        title: str = "Revenue Predictions vs Actual Data"
    ) -> go.Figure:
        """
        Create comparison chart with actual data and predictions.
        
        Args:
            actual_data: DataFrame with actual revenue (date, actual_revenue columns)
            pred_latest: DataFrame with latest predictions (date, prediction columns)
            pred_second: DataFrame with second latest predictions
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        fig = go.Figure()
        
        # Add actual data
        fig.add_trace(go.Scatter(
            x=actual_data['date'],
            y=actual_data['actual_revenue'],
            mode='lines+markers',
            name='Actual Revenue',
            line=dict(color='#2E86AB', width=3),
            marker=dict(size=8),
            hovertemplate='<b>Actual</b><br>Date: %{x|%Y-%m-%d}<br>Revenue: $%{y:,.2f}<extra></extra>'
        ))
        
        # Add latest prediction
        fig.add_trace(go.Scatter(
            x=pred_latest['date'],
            y=pred_latest['prediction'],
            mode='lines+markers',
            name='Latest Prediction',
            line=dict(color='#A23B72', width=2, dash='dash'),
            marker=dict(size=6),
            hovertemplate='<b>Latest Pred</b><br>Date: %{x|%Y-%m-%d}<br>Forecast: $%{y:,.2f}<extra></extra>'
        ))
        
        # Add second prediction if available
        if not pred_second.empty:
            fig.add_trace(go.Scatter(
                x=pred_second['date'],
                y=pred_second['prediction'],
                mode='lines+markers',
                name='Previous Prediction',
                line=dict(color='#F18F01', width=2, dash='dot'),
                marker=dict(size=6),
                hovertemplate='<b>Prev Pred</b><br>Date: %{x|%Y-%m-%d}<br>Forecast: $%{y:,.2f}<extra></extra>'
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title='Date',
            yaxis_title='Revenue ($)',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            font=dict(size=12),
            legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.8)')
        )
        
        return fig
    
    def calculate_metrics(
        self,
        actual_data: pd.DataFrame,
        pred_latest: pd.DataFrame,
        pred_second: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Calculate evaluation metrics (MAE, RMSE, MAPE).
        
        Args:
            actual_data: DataFrame with actual values
            pred_latest: DataFrame with latest predictions
            pred_second: DataFrame with second predictions (optional)
            
        Returns:
            Dictionary with metrics
        """
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        import numpy as np
        
        metrics = {}
        
        # Merge predictions with actual data on date
        merged_latest = pd.merge(
            actual_data[['date', 'actual_revenue']],
            pred_latest[['date', 'prediction']],
            on='date',
            how='inner'
        )
        
        if not merged_latest.empty:
            actual = merged_latest['actual_revenue'].values
            pred = merged_latest['prediction'].values
            
            mae = mean_absolute_error(actual, pred)
            rmse = np.sqrt(mean_squared_error(actual, pred))
            mape = np.mean(np.abs((actual - pred) / actual)) * 100
            
            metrics['latest'] = {
                'MAE': mae,
                'RMSE': rmse,
                'MAPE': mape,
                'samples': len(merged_latest)
            }
        
        # Calculate for second prediction if provided
        if pred_second is not None and not pred_second.empty:
            merged_second = pd.merge(
                actual_data[['date', 'actual_revenue']],
                pred_second[['date', 'prediction']],
                on='date',
                how='inner'
            )
            
            if not merged_second.empty:
                actual = merged_second['actual_revenue'].values
                pred = merged_second['prediction'].values
                
                mae = mean_absolute_error(actual, pred)
                rmse = np.sqrt(mean_squared_error(actual, pred))
                mape = np.mean(np.abs((actual - pred) / actual)) * 100
                
                metrics['previous'] = {
                    'MAE': mae,
                    'RMSE': rmse,
                    'MAPE': mape,
                    'samples': len(merged_second)
                }
        
        return metrics
    
    def create_metrics_table(self, metrics: Dict) -> go.Figure:
        """
        Create metrics comparison table.
        
        Args:
            metrics: Dictionary with calculated metrics
            
        Returns:
            Plotly figure with metrics table
        """
        rows = []
        for model_name, model_metrics in metrics.items():
            rows.append([
                model_name.replace('_', ' ').title(),
                f"${model_metrics['MAE']:,.2f}",
                f"${model_metrics['RMSE']:,.2f}",
                f"{model_metrics['MAPE']:.2f}%",
                model_metrics['samples']
            ])
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=['<b>Model</b>', '<b>MAE</b>', '<b>RMSE</b>', '<b>MAPE</b>', '<b>Samples</b>'],
                fill_color='#2E86AB',
                align='center',
                font=dict(color='white', size=12)
            ),
            cells=dict(
                values=list(zip(*rows)) if rows else [[], [], [], [], []],
                fill_color='lavender',
                align='center',
                font=dict(size=11),
                height=25
            )
        )])
        
        fig.update_layout(
            title='Model Evaluation Metrics',
            height=250,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        return fig
    
    def create_residuals_chart(
        self,
        actual_data: pd.DataFrame,
        pred_latest: pd.DataFrame,
        pred_second: Optional[pd.DataFrame] = None
    ) -> go.Figure:
        """
        Create residuals analysis chart.
        
        Args:
            actual_data: DataFrame with actual values
            pred_latest: DataFrame with latest predictions
            pred_second: DataFrame with second predictions
            
        Returns:
            Plotly figure with residuals
        """
        fig = go.Figure()
        
        # Calculate residuals for latest prediction
        merged_latest = pd.merge(
            actual_data[['date', 'actual_revenue']],
            pred_latest[['date', 'prediction']],
            on='date',
            how='inner'
        )
        
        if not merged_latest.empty:
            residuals_latest = merged_latest['actual_revenue'] - merged_latest['prediction']
            
            fig.add_trace(go.Scatter(
                x=merged_latest['date'],
                y=residuals_latest,
                mode='lines+markers',
                name='Latest Residuals',
                line=dict(color='#A23B72', width=2),
                marker=dict(size=6),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Residual: $%{y:,.2f}<extra></extra>'
            ))
        
        # Add residuals for second prediction if available
        if pred_second is not None and not pred_second.empty:
            merged_second = pd.merge(
                actual_data[['date', 'actual_revenue']],
                pred_second[['date', 'prediction']],
                on='date',
                how='inner'
            )
            
            if not merged_second.empty:
                residuals_second = merged_second['actual_revenue'] - merged_second['prediction']
                
                fig.add_trace(go.Scatter(
                    x=merged_second['date'],
                    y=residuals_second,
                    mode='lines+markers',
                    name='Previous Residuals',
                    line=dict(color='#F18F01', width=2, dash='dash'),
                    marker=dict(size=6),
                    hovertemplate='Date: %{x|%Y-%m-%d}<br>Residual: $%{y:,.2f}<extra></extra>'
                ))
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Zero Error")
        
        fig.update_layout(
            title='Residuals Analysis',
            xaxis_title='Date',
            yaxis_title='Residual ($)',
            hovermode='x unified',
            template='plotly_white',
            height=400,
            font=dict(size=12)
        )
        
        return fig
    
    def generate_dashboard(
        self,
        actual_file: str,
        predictions_file: str,
        output_name: str = "prediction_dashboard.html"
    ) -> str:
        """
        Generate complete interactive dashboard.
        
        Args:
            actual_file: Path to actual data CSV
            predictions_file: Path to predictions CSV
            output_name: Name of output HTML file
            
        Returns:
            Path to generated dashboard file
        """
        # Load data
        actual_data = self.load_actual_data(actual_file)
        predictions_df = self.load_predictions(predictions_file)
        
        # Get last two predictions
        pred_latest, pred_second = self.get_latest_two_predictions(predictions_df)
        
        # Create charts
        comparison_fig = self.create_comparison_chart(actual_data, pred_latest, pred_second)
        metrics = self.calculate_metrics(actual_data, pred_latest, pred_second)
        metrics_fig = self.create_metrics_table(metrics)
        residuals_fig = self.create_residuals_chart(actual_data, pred_latest, pred_second)
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Predictions vs Actual', 'Evaluation Metrics', 'Residuals Analysis'),
            specs=[[{}], [{}], [{}]],
            row_heights=[0.5, 0.2, 0.3],
            vertical_spacing=0.12
        )
        
        # Add comparison traces
        for trace in comparison_fig.data:
            fig.add_trace(trace, row=1, col=1)
        
        # Add metrics table
        for trace in metrics_fig.data:
            fig.add_trace(trace, row=2, col=1)
        
        # Add residuals
        for trace in residuals_fig.data:
            fig.add_trace(trace, row=3, col=1)
        
        # Update layout
        fig.update_xaxes(title_text='Date', row=1, col=1)
        fig.update_xaxes(title_text='Date', row=3, col=1)
        fig.update_yaxes(title_text='Revenue ($)', row=1, col=1)
        fig.update_yaxes(title_text='Residual ($)', row=3, col=1)
        
        fig.update_layout(
            title_text='Revenue Prediction Dashboard',
            height=1200,
            showlegend=True,
            template='plotly_white',
            font=dict(size=11)
        )
        
        # Save dashboard
        output_path = self.output_dir / output_name
        fig.write_html(str(output_path))
        
        print(f"Dashboard generated: {output_path}")
        return str(output_path)


# Example usage
if __name__ == "__main__":
    dashboard = DashboardGenerator(output_dir="dashboards")
    
    # Example: Generate dashboard
    # dashboard.generate_dashboard(
    #     actual_file="data/actual_revenue.csv",
    #     predictions_file="data/model_predictions.csv",
    #     output_name="revenue_dashboard.html"
    # )
    
    print("Dashboard generator initialized and ready to use.")
