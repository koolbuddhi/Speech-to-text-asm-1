# Use the official Python image as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies for building pyaudio
RUN apt-get update && apt-get install -y \
    gcc \
    libasound2-dev \
    build-essential\
    portaudio19-dev \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=app.py


# Use a .env file to manage sensitive information securely
# Ensure your .env file is added to .gitignore

# Run app.py when the container launches
CMD ["flask", "run", "--host=0.0.0.0"]
