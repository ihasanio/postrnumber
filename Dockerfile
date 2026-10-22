FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the FastAPI port
EXPOSE 8083

# Command to run the FastAPI app
CMD ["uvicorn", "custom_post_runner:app", "--host", "0.0.0.0", "--port", "8083"]
