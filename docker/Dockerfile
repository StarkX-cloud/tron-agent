FROM python:3.11-slim

RUN pip install docker

WORKDIR /app

COPY tron/observer.py .

RUN mkdir -p /logs

CMD ["python", "observer.py"]
