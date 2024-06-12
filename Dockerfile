# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openvpn \
    xvfb \
    wget \
    gnupg2 \
    software-properties-common

# Install Google Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -f -y && \
rm google-chrome-stable_current_amd64.deb

# Copy the requirements.txt file into the container at /app
COPY requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.json
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the rest of the application
COPY . /app
