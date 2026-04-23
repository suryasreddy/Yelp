FROM python:3.11-slim
WORKDIR /app
COPY services/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services /app/services
COPY scripts /app/scripts
ENV PYTHONPATH=/app
CMD ["python", "-m", "services.review_worker.worker"]
