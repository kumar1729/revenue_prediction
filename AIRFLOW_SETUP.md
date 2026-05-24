# Apache Airflow Setup for Revenue Prediction

This guide helps you set up Apache Airflow to run your revenue prediction library daily at 2 PM UTC.

## Prerequisites

- Python 3.8+
- pip package manager
- Virtual environment (recommended)

## Installation

### 1. Create and activate a virtual environment

```bash
python -m venv airflow_env
source airflow_env/bin/activate  # On Windows: airflow_env\Scripts\activate
```

### 2. Install Apache Airflow

```bash
pip install -r requirements-airflow.txt
```

### 3. Initialize Airflow database

```bash
airflow db init
```

### 4. Create an admin user

```bash
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

## Running Airflow

### Terminal 1: Start the Scheduler

```bash
airflow scheduler
```

### Terminal 2: Start the Web UI

```bash
airflow webui
```

Then open your browser and go to `http://localhost:8080`

## Using Your DAG

1. Log in with username: `admin` and password: `admin`
2. Find the `revenue_prediction_daily` DAG in the list
3. Click the toggle switch to enable it
4. The DAG will run automatically at **2 PM UTC every day**

## Customizing the Schedule

To change the execution time, edit `dags/revenue_prediction_dag.py` and modify the `schedule_interval`:

```python
schedule_interval='0 14 * * *',  # Change this cron expression
```

### Common cron expressions:
- `0 14 * * *` - 2 PM UTC daily
- `0 9 * * *` - 9 AM UTC daily
- `0 14 * * MON` - 2 PM UTC every Monday
- `*/30 * * * *` - Every 30 minutes

## Production Deployment

For production environments, consider:

1. **Use a managed Airflow service** (AWS MWAA, Google Cloud Composer, Astronomer)
2. **Run on a dedicated server** with systemd/supervisor
3. **Configure database** (PostgreSQL, MySQL) instead of SQLite
4. **Set up monitoring** and alerting
5. **Use environment variables** for sensitive data

## Troubleshooting

### DAG not showing up
```bash
airflow dags list
```

### Check DAG syntax
```bash
airflow dags validate
```

### View logs
```bash
airflow logs -d revenue_prediction_daily
```

### Reset the database
```bash
airflow db reset  # WARNING: This deletes all data
```

## Next Steps

1. Update `dags/revenue_prediction_dag.py` with your library imports
2. Add your project dependencies to `requirements-airflow.txt`
3. Test the DAG locally before deploying to production
4. Set up monitoring and alerting for failures
