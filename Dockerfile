# Use the official lightweight Python 3.11 image as the base
FROM python:3.12-slim

# Set working directory
WORKDIR /etl_microsoftsql_spinotale

# Install system dependencies and Microsoft ODBC Driver
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc \
    unixodbc-dev \
    build-essential \
    && mkdir -p /etc/apt/keyrings \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64,arm64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && printf "[ODBC Driver 18 for SQL Server]\nDescription=Microsoft ODBC Driver 18 for SQL Server\nDriver=$(find /opt/microsoft/msodbcsql18/ -name 'libmsodbcsql-18*.so*' | head -n 1)\nUsageCount=1\n" >> /etc/odbcinst.ini \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user for GKE Autopilot security
RUN useradd -m etluser
USER etluser

# Copy application code
COPY . .

# Default command (can be overridden by K8s 'command' field)
CMD ["python", "-m", "routes.run_cron_job"]