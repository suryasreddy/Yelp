FROM python:3.11-slim
WORKDIR /app
COPY services/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services /app/services
COPY scripts /app/scripts
ENV PYTHONPATH=/app
EXPOSE 8001
CMD ["uvicorn", "services.user_reviewer_service.app:app", "--host", "0.0.0.0", "--port", "8001"]
