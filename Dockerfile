FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app
COPY migrations /app/migrations
COPY run.py /app/run.py

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "run.py"]
