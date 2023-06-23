# Use python image
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1 \
	PIP_NO_CACHE_DIR=off \
	PIP_DISABLE_PIP_VERSION_CHECK=on \
	PIP_DEFAULT_TIMEOUT=100

# Set working directory
WORKDIR /code

# Copy requirements.text file
COPY ./requirements.txt /code/requirements.txt

# Install dependencies with caching
RUN pip install -r /code/requirements.txt

# Copy the app
COPY ./app /code/app

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]