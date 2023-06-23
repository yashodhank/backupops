# Backup Docker Container Service Documentation

This documentation provides detailed instructions for setting up and configuring the backup Docker container service. The service is designed to perform automatic backups of files and databases for Plesk users, upload the backups to Wasabi S3, and log backup information in a Google Spreadsheet. It also includes features such as Telegram and Pushover alerts, disk space monitoring, and reporting of CPU and RAM availability.

## Prerequisites

Before setting up the backup Docker container service, ensure that you have the following prerequisites:

- Docker installed on the host server
- Access to the following API keys and credentials:
  - Telegram Bot API key
  - Pushover App token and user key
  - Google Service Account credentials (JSON file)
  - Wasabi S3 access key and secret access key

## Setup Instructions

Follow these step-by-step instructions to set up and configure the backup Docker container service:

1. Clone the repository or create a new directory for the backup service.

2. Create a Docker Compose file named `docker-compose.yml` with the following content:

```yaml
version: "3"
services:
  backup:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      # Telegram Bot Token
      - TELEGRAM_TOKEN=<your_telegram_bot_token>

      # Telegram Chat IDs (comma-separated list)
      - TELEGRAM_CHAT_IDS=<telegram_chat_ids>

      # Pushover App Token (optional)
      - PUSHOVER_APP_TOKEN=<pushover_app_token>

      # Pushover User Key (optional)
      - PUSHOVER_USER_KEY=<pushover_user_key>

      # Google Spreadsheet credentials (JSON key)
      - GOOGLE_PROJECT_ID=<google_project_id>
      - GOOGLE_PRIVATE_KEY_ID=<google_private_key_id>
      - GOOGLE_PRIVATE_KEY=<google_private_key>
      - GOOGLE_CLIENT_EMAIL=<google_client_email>
      - GOOGLE_CLIENT_ID=<google_client_id>
      - GOOGLE_CLIENT_X509_CERT_URL=<google_client_x509_cert_url>

      # Plesk backup settings
      - PLESK_BACKUP_DIR=/var/lib/psa/dumps/
      - PLESK_FILE_BACKUP_PREFIX=file_backup_
      - PLESK_DB_BACKUP_PREFIX=db_backup_

      # Wasabi S3 settings
      - WASABI_BUCKET_NAME=<wasabi_bucket_name>
      - WASABI_ACCESS_KEY_ID=<wasabi_access_key_id>
      - WASABI_SECRET_ACCESS_KEY=<wasabi_secret_access_key>

      # AWS S3 settings
      - AWS_REGION=us-east-1
      - AWS_ENDPOINT_URL=https://s3.wasabisys.com

      # Backup destination directory
      - BACKUP_DESTINATION=/app/backups/

      # Rotation settings
      - ROTATE_AFTER_DAYS=90

      # Failed backup count for Pushover emergency notification (optional)
      - PUSHOVER_FAILURE_THRESHOLD=3

      # Google Spreadsheet name (optional)
      - GOOGLE_SPREADSHEET_NAME=<google_spreadsheet_name>

    volumes:
      - /var/lib/psa/dumps/:/var/lib/psa/dumps/
      - ./backup.py:/app/backup.py
      - ./requirements.txt:/app/requirements.txt
```

Replace the `your_*` placeholders with the actual values for the corresponding environment variables. Adjust the environment variable names based on your Docker image's configuration.

3. Build the Docker image using the following command:

```bash
docker-compose build
```

4. Run the backup service using the following command:

```bash
docker-compose up -d
```

The backup process will start automatically based on the specified schedule (e.g., daily).

## Configuration and Customization

### Telegram Configuration

To configure Telegram for backup alerts:

1. Create a Telegram Bot by following the instructions in the [Telegram Bot API documentation](https://core.telegram.org/bots#botfather).
2. Obtain the Telegram Bot API key for your bot.
3. Identify the chat ID(s) of the Telegram channel(s) or group(s) where you want to receive backup alerts.

### Pushover Configuration

To configure Pushover for backup alerts:

1. Create a Pushover account if you don't have one already.
2. Create a new application in Pushover to obtain the App token.
3. Obtain the User key for your Pushover account.

### Google Spreadsheet Configuration

To configure Google Spreadsheet for backup logs:

1. Create a Google

 Service Account by following the instructions in the [Google Cloud documentation](https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account).
2. Generate a JSON key file for the Service Account and keep it secure.
3. Share the desired Google Spreadsheet with the Service Account email address.
4. Obtain the required credentials from the JSON key file:
   - `project_id`: The project ID associated with the Google Service Account.
   - `private_key_id`: The private key ID from the JSON key file.
   - `private_key`: The private key from the JSON key file (replace newlines with `\n`).
   - `client_email`: The client email address from the JSON key file.
   - `client_id`: The client ID from the JSON key file.
   - `client_x509_cert_url`: The client x509 certificate URL from the JSON key file.

### Wasabi S3 Configuration

To configure Wasabi S3 for backup storage:

1. Sign up for a Wasabi S3 account if you don't have one already.
2. Create a new bucket to store the backups.
3. Obtain the access key and secret access key for the Wasabi S3 account.

### Optional Configuration

The backup Docker container service provides additional optional configuration:

- Adjust the `ROTATE_AFTER_DAYS` environment variable to change the rotation period for backups (default is 90 days).
- Adjust the `PUSHOVER_FAILURE_THRESHOLD` environment variable to set the number of consecutive backup failures before triggering an emergency Pushover notification (default is 3).

## Monitoring and Troubleshooting

- Monitor the Telegram channel/group and Pushover notifications for backup updates and failure alerts.
- Access the Google Spreadsheet to view the backup logs and details.
- If a backup fails, check the Telegram message, Pushover alert, and the Google Spreadsheet logs for detailed information.
- If the backup fails due to issues with CPU, RAM, or storage, the Telegram message and Pushover alert will include the available CPU and RAM information.

## Conclusion

Congratulations! You have successfully set up and configured the backup Docker container service. The service will automatically perform backups of files and databases, upload them to Wasabi S3, and log backup information in a Google Spreadsheet. You will receive alerts via Telegram and Pushover for backup updates and failures. Monitor the Telegram channel/group, Pushover notifications, and the Google Spreadsheet logs to ensure the backups are running smoothly.

If you have any questions or encounter any issues, please refer to the respective documentation for the APIs and services used, or feel free to reach out for assistance.

**Note**: Ensure that you regularly monitor the backups, storage utilization, and any notifications received to ensure the integrity and availability of your backups.

## Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots#botfather)
- [Pushover Documentation](https://pushover.net/api)
- [Google Cloud Service Account Documentation](https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account)
- [Wasabi S3 Documentation](https://wasabi-support.zendesk.com/hc/en-us/categories/360000030391-Getting-Started)
- [Docker Documentation](https://docs.docker.com/)

Please refer to the provided URLs for detailed information and guidance on the respective APIs and services.

---

Feel free to customize and enhance the documentation as per your specific requirements and environment.

If you have any further questions or need additional assistance, please let me know!