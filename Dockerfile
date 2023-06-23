# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install

# Install required Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backup script and credentials
COPY backup.py /app/backup.py
COPY credentials.json /app/credentials.json

# Set environment variables
ENV GOOGLE_SPREADSHEET_NAME="your-spreadsheet-name"
ENV TELEGRAM_TOKEN="your-telegram-token"
ENV TELEGRAM_CHAT_IDS="chat-id1,chat-id2"
ENV PUSHOVER_APP_TOKEN="your-pushover-app-token"
ENV PUSHOVER_USER_KEY="your-pushover-user-key"
ENV WASABI_BUCKET_NAME="your-wasabi-bucket-name"
ENV WASABI_ACCESS_KEY_ID="your-wasabi-access-key-id"
ENV WASABI_SECRET_ACCESS_KEY="your-wasabi-secret-access-key"
ENV AWS_REGION="your-aws-region"
ENV AWS_ENDPOINT_URL="your-aws-endpoint-url"
ENV ROTATE_AFTER_DAYS="90"
ENV PUSHOVER_FAILURE_THRESHOLD="3"

# Run the backup script
CMD [ "python", "backup.py" ]
