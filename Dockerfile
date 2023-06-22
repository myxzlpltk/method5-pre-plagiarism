# Use python image
FROM python:3.10-slim

# Set working directory
WORKDIR /code

# Copy requirements.text file
COPY ./requirements.txt /code/requirements.txt

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache \
	pip install -r /code/requirements.txt

# Copy the app
COPY ./app /code/app

# Expose port
EXPOSE 80

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]