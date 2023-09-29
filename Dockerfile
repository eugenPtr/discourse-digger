# Use an official Python runtime as a parent image
FROM python:3.11.5-bookworm

# Set the working directory
WORKDIR /

# Copy the requirements file into the container and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY schema.prisma .
RUN prisma generate

# Copy the rest of the application code into the container
COPY main.py .

# Run the command to start the application
CMD ["python", "main.py"]