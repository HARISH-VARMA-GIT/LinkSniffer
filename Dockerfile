# Use the Ubuntu 22.04 base image
FROM ubuntu:22.04

# Add Python 3.8 to the image
FROM python:3.10


# Update package lists for the Ubuntu system
RUN apt-get update

# Install the 'unzip' package
RUN apt install unzip

# Copy the Chrome Debian package to the image
COPY chrome_114_amd64.deb ./

# Install the Chrome Debian package
RUN apt install ./chrome_114_amd64.deb -y

# Download ChromeDriver binary version 114.0.5735.90 for Linux
RUN wget https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip

# Unzip the downloaded ChromeDriver binary
RUN unzip chromedriver_linux64.zip

# Move the ChromeDriver binary to /usr/bin
RUN mv chromedriver /usr/bin/chromedriver

# Print the version of Google Chrome installed
RUN google-chrome --version

# Set the working directory inside the image to /app
WORKDIR /project

# Copy the requirements.txt file to /app
COPY requirements.txt .

# Install Python dependencies listed in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script 'app.py' to /app
COPY . .

# Specify the default command to execute when the container starts
ENTRYPOINT [ "python", "app/main.py"]