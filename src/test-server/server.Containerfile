# Use a lightweight, official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the server script into the container
COPY server.py .

# Expose the default port (documentation only)
EXPOSE 8000

# Run the script when the container starts
CMD ["python", "server.py"]