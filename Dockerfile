FROM python:3.14

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir -r /code/requirements.txt

COPY ./src /code/src

ENV PYTHONPATH=/code/src:$PYTHONPATH

EXPOSE 8000

CMD ["uvicorn", "forecast_pipeline.server:app", "--host", "0.0.0.0", "--port", "8000"]
