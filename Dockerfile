# Use an official Python runtime as a parent image
FROM python:3.11.5-bookworm

# Set the working directory
WORKDIR /

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY pyproject.toml .
COPY schema.prisma .
COPY src/utils/initialize_db.py .

COPY src/cronjob.py .


# Run the initialization script followed by the main application
CMD ["sh", "-c", "prisma db push && pyright && python initialize_db.py && python cronjob.py"]