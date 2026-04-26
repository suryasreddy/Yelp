FROM python:3.11-slim
WORKDIR /app
COPY services/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services /app/services
COPY scripts /app/scripts
ENV PYTHONPATH=/app
EXPOSE 8003
CMD ["uvicorn", "services.restaurant_owner_service.app:app", "--host", "0.0.0.0", "--port", "8003"]
