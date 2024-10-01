# Dockerfile

# Use the official Python image as a base
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Copy the .env file into the container
COPY .env /app/.env

# Install required packages, including SQLite
RUN apt-get update && apt-get install -y sqlite3

# Create /data directory for the database and set permissions
RUN mkdir -p /data && chmod 777 /data

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5001 for the Flask web server
EXPOSE 5001

# Define the command to run the app
CMD ["python", "app.py"]
