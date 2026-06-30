# Use a lightweight, official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the server script into the container
COPY client.py .

# Run the script when the container starts
CMD ["python", "client.py"]