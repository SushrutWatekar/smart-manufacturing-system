# Use Python slim image for smaller size
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main application file into the container
COPY main.py .

# Expose the application port
EXPOSE 8004

# Define the default command to run the application
CMD ["sh", "-c", "sleep 10 && python main.py"]
