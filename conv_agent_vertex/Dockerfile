# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY app/ .

# Expose the port the app runs on
EXPOSE 5000

# Run the Flask application
# CMD ["python", "main.py"] # For development
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]