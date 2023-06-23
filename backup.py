import os
import shutil
import subprocess
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import telebot
from urllib.parse import quote_plus
import psutil

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Telegram Chat IDs
TELEGRAM_CHAT_IDS = os.getenv('TELEGRAM_CHAT_IDS').split(',')

# Pushover App Token
PUSHOVER_APP_TOKEN = os.getenv('PUSHOVER_APP_TOKEN')

# Pushover User Key
PUSHOVER_USER_KEY = os.getenv('PUSHOVER_USER_KEY')

# Google Spreadsheet credentials
SPREADSHEET_CREDENTIALS = {
    "type": "service_account",
    "project_id": os.getenv('GOOGLE_PROJECT_ID'),
    "private_key_id": os.getenv('GOOGLE_PRIVATE_KEY_ID'),
    "private_key": os.getenv('GOOGLE_PRIVATE_KEY').replace('\\n', '\n'),
    "client_email": os.getenv('GOOGLE_CLIENT_EMAIL'),
    "client_id": os.getenv('GOOGLE_CLIENT_ID'),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://accounts.google.com/o/oauth2/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv('GOOGLE_CLIENT_X509_CERT_URL')
}

# Plesk backup settings
PLESK_BACKUP_DIR = "/var/lib/psa/dumps/"
PLESK_FILE_BACKUP_PREFIX = "file_backup_"
PLESK_DB_BACKUP_PREFIX = "db_backup_"

# Wasabi S3 settings
WASABI_BUCKET_NAME = os.getenv('WASABI_BUCKET_NAME')
WASABI_ACCESS_KEY_ID = os.getenv('WASABI_ACCESS_KEY_ID')
WASABI_SECRET_ACCESS_KEY = os.getenv('WASABI_SECRET_ACCESS_KEY')

# AWS S3 settings
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL', 'https://s3.wasabisys.com')

# Backup destination directory
BACKUP_DESTINATION = "/app/backups/"

# Rotation settings
ROTATE_AFTER_DAYS = int(os.getenv('ROTATE_AFTER_DAYS', '90'))

# Failed backup count for Pushover emergency notification
PUSHOVER_FAILURE_THRESHOLD = int(os.getenv('PUSHOVER_FAILURE_THRESHOLD', '3'))


def create_backup_directory():
    if not os.path.exists(BACKUP_DESTINATION):
        os.makedirs(BACKUP_DESTINATION)


def create_backup():
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")

    # Backup files for all active Plesk users
    users = find_active_plesk_users()
    for user in users:
        user_files_backup_file_name = PLESK_FILE_BACKUP_PREFIX + \
            user + "_" + current_time + ".tar"
        user_files_backup_file_path = os.path.join(
            BACKUP_DESTINATION, user_files_backup_file_name)
        plesk_user_files_path = find_plesk_user_files_path(user)
        shutil.make_archive(user_files_backup_file_path,
                            "gztar", plesk_user_files_path)

    # Backup databases for all active Plesk users
    databases_backup_file_names = []
    for user in users:
        user_databases = find_plesk_user_databases(user)
        for database_info in user_databases:
            database_type, database_name = database_info
            database_backup_file_name = PLESK_DB_BACKUP_PREFIX + \
                database_type + "_" + database_name + "_" + current_time + ".sql"
            database_backup_file_path = os.path.join(
                BACKUP_DESTINATION, database_backup_file_name)
            backup_database(database_type, database_name,
                            database_backup_file_path)
            databases_backup_file_names.append(database_backup_file_name)

    return current_time, user_files_backup_file_names, databases_backup_file_names


def find_active_plesk_users():
    users = []
    command = "plesk bin user --list"
    output = subprocess.check_output(
        command, shell=True, universal_newlines=True)
    for line in output.splitlines():
        if "client" in line:
            user = line.split("|")[3].strip()
            users.append(user)
    return users


def find_plesk_user_files_path(user):
    command = f"plesk bin user --info {user}"
    output = subprocess.check_output(
        command, shell=True, universal_newlines=True)
    for line in output.splitlines():
        if "Home directory" in line:
            return line.split("|")[2].strip()
    return None


def find_plesk_user_databases(user):
    databases = []
    # Find MySQL databases
    command_mysql = f"plesk db -Ne 'SELECT name FROM data_bases WHERE dom_id IN (SELECT id FROM domains WHERE name=\"{user}\") AND type=\"mysql\"'"
    output_mysql = subprocess.check_output(
        command_mysql, shell=True, universal_newlines=True)
    for line in output_mysql.splitlines():
        databases.append(("mysql", line.strip()))

    # Find PostgreSQL databases
    command_postgres = f"plesk db -Ne 'SELECT name FROM data_bases WHERE dom_id IN (SELECT id FROM domains WHERE name=\"{user}\") AND type=\"postgresql\"'"
    output_postgres = subprocess.check_output(
        command_postgres, shell=True, universal_newlines=True)
    for line in output_postgres.splitlines():
        databases.append(("postgresql", line.strip()))

    return databases


def backup_database(database_type, database_name, backup_file_path):
    if database_type == "mysql":
        command = f"plesk db dump {database_name} --result-file={backup_file_path}"
        os.system(command)
    elif database_type == "postgresql":
        command = f"pg_dump -U postgres -Fc {database_name} > {backup_file_path}"
        os.system(command)


def upload_to_wasabi_s3(current_time, user_files_backup_file_names, databases_backup_file_names):
    # Upload files to Wasabi S3 bucket
    for backup_file_name in user_files_backup_file_names:
        local_file_path = os.path.join(BACKUP_DESTINATION, backup_file_name)
        s3_folder_path = get_s3_folder_path(current_time, backup_file_name)
        s3_file_path = f"{s3_folder_path}/{backup_file_name}"
        upload_to_s3(local_file_path, s3_file_path)

    # Upload databases to Wasabi S3 bucket
    for backup_file_name in databases_backup_file_names:
        local_file_path = os.path.join(BACKUP_DESTINATION, backup_file_name)
        s3_folder_path = get_s3_folder_path(current_time, backup_file_name)
        s3_file_path = f"{s3_folder_path}/{backup_file_name}"
        upload_to_s3(local_file_path, s3_file_path)


def upload_to_s3(local_file_path, s3_file_path):
    command = f"aws s3 cp {local_file_path} s3://{WASABI_BUCKET_NAME}/{s3_file_path} \
                --region {AWS_REGION} --endpoint-url {AWS_ENDPOINT_URL} \
                --no-verify-ssl --access-key {WASABI_ACCESS_KEY_ID} --secret-key {WASABI_SECRET_ACCESS_KEY}"
    os.system(command)


def get_s3_folder_path(current_time, backup_file_name):
    server_public_ip = get_public_ip()
    username = backup_file_name.split("_")[2]
    folder_name = f"{server_public_ip}/{username}/{current_time}"
    return folder_name


def upload_to_google_spreadsheet(current_time, user_files_backup_file_names, databases_backup_file_names):
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        SPREADSHEET_CREDENTIALS, scope)
    client = gspread.authorize(credentials)

    # Get or create the Google Spreadsheet
    spreadsheet_name = os.getenv(
        'GOOGLE_SPREADSHEET_NAME', f"backuposp_{get_public_ip()}")
    spreadsheet = get_or_create_spreadsheet(client, spreadsheet_name)

    # Upload backup information to Google Spreadsheet
    for user, user_files_backup_file_name in zip(find_active_plesk_users(), user_files_backup_file_names):
        worksheet = get_or_create_worksheet(spreadsheet, user)
        upload_backup_info_to_worksheet(
            worksheet, current_time, user_files_backup_file_name, "File Backup")

    for user, database_backup_file_name in zip(find_active_plesk_users(), databases_backup_file_names):
        worksheet = get_or_create_worksheet(spreadsheet, user)
        upload_backup_info_to_worksheet(
            worksheet, current_time, database_backup_file_name, "Database Backup")


def get_or_create_spreadsheet(client, spreadsheet_name):
    try:
        return client.open(spreadsheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        return client.create(spreadsheet_name)


def get_or_create_worksheet(spreadsheet, worksheet_name):
    try:
        return spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(worksheet_name, 1, 1)


def upload_backup_info_to_worksheet(worksheet, current_time, backup_file_name, backup_type):
    s3_file_url = get_s3_file_url(current_time, backup_file_name)
    row_data = [current_time, backup_file_name,
                s3_file_url, backup_type, "", "", "", ""]
    worksheet.append_row(row_data)


def get_s3_file_url(current_time, backup_file_name):
    s3_folder_path = get_s3_folder_path(current_time, backup_file_name)
    s3_file_path = f"{s3_folder_path}/{backup_file_name}"
    return f"{AWS_ENDPOINT_URL}/{quote_plus(WASABI_BUCKET_NAME)}/{quote_plus(s3_file_path)}"


def send_telegram_alert(message):
    for chat_id in TELEGRAM_CHAT_IDS:
        bot = telebot.TeleBot(TELEGRAM_TOKEN)
        bot.send_message(chat_id, message)


def send_pushover_alert(message):
    if PUSHOVER_APP_TOKEN and PUSHOVER_USER_KEY:
        pushover_url = "https://api.pushover.net/1/messages.json"
        data = {
            "token": PUSHOVER_APP_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "title": "Backup Failure",
            "message": message,
            "priority": 1
        }
        subprocess.run(["curl", "-s", "-X", "POST", pushover_url, "-F",
                       f"token={PUSHOVER_APP_TOKEN}", "-F", f"user={PUSHOVER_USER_KEY}", "-F", f"title=Backup Failure", "-F", f"message={message}", "-F", "priority=1"])


def delete_temp_backups():
    backups = os.listdir(BACKUP_DESTINATION)
    for backup in backups:
        backup_path = os.path.join(BACKUP_DESTINATION, backup)
        os.remove(backup_path)


def rotate_backups():
    rotation_date = datetime.now() - timedelta(days=ROTATE_AFTER_DAYS)
    rotation_date_str = rotation_date.strftime("%Y%m%d")

    backups = os.listdir(BACKUP_DESTINATION)
    for backup in backups:
        backup_date_str = backup.split("_")[-1].split(".")[0]
        if backup_date_str <= rotation_date_str:
            backup_path = os.path.join(BACKUP_DESTINATION, backup)
            if os.path.isfile(backup_path):
                os.remove(backup_path)
            elif os.path.isdir(backup_path):
                shutil.rmtree(backup_path)


def get_public_ip():
    return os.popen('curl -s http://checkip.amazonaws.com').read().strip()


def check_disk_space():
    command = "df -h / | tail -1"
    output = subprocess.check_output(
        command, shell=True, universal_newlines=True)
    disk_space_info = output.split()
    total_size = disk_space_info[1]
    used_size = disk_space_info[2]
    available_size = disk_space_info[3]
    percentage_used = disk_space_info[4]
    return total_size, used_size, available_size, percentage_used


def get_system_stats():
    cpu_percent = psutil.cpu_percent(interval=1)
    ram_percent = psutil.virtual_memory().percent
    total_size, used_size, available_size, percentage_used = check_disk_space()
    return cpu_percent, ram_percent, total_size, used_size, available_size, percentage_used


def main():
    try:
        create_backup_directory()
        current_time, user_files_backup_file_names, databases_backup_file_names = create_backup()
        upload_to_wasabi_s3(
            current_time, user_files_backup_file_names, databases_backup_file_names)
        upload_to_google_spreadsheet(
            current_time, user_files_backup_file_names, databases_backup_file_names)
        cpu_percent, ram_percent, total_size, used_size, available_size, percentage_used = get_system_stats()
        message = generate_telegram_message(current_time, user_files_backup_file_names, databases_backup_file_names,
                                            cpu_percent, ram_percent, total_size, used_size, available_size, percentage_used)
        send_telegram_alert(message)
        delete_temp_backups()
        rotate_backups()
    except Exception as e:
        send_telegram_alert(f"Backup failed with error: {str(e)}")
        send_pushover_alert(f"Backup failed with error: {str(e)}")


def generate_telegram_message(current_time, user_files_backup_file_names, databases_backup_file_names, cpu_percent, ram_percent, total_size, used_size, available_size, percentage_used):
    server_public_ip = get_public_ip()

    message = f"Backup completed successfully at {current_time}\n\n"
    message += "Backup Summary:\n"

    message += "User Files Backup:\n"
    for backup_file_name in user_files_backup_file_names:
        username = backup_file_name.split("_")[2]
        s3_file_url = get_s3_file_url(current_time, backup_file_name)
        message += f"Username: {username}\n"
        message += f"Backup File: {backup_file_name}\n"
        message += f"Backup URL: {s3_file_url}\n\n"

    message += "Database Backup:\n"
    for backup_file_name in databases_backup_file_names:
        database_type = backup_file_name.split("_")[2]
        database_name = backup_file_name.split("_")[3].split(".")[0]
        s3_file_url = get_s3_file_url(current_time, backup_file_name)
        message += f"Database Type: {database_type}\n"
        message += f"Database Name: {database_name}\n"
        message += f"Backup File: {backup_file_name}\n"
        message += f"Backup URL: {s3_file_url}\n\n"

    message += "Server Information:\n"
    message += f"Public IP: {server_public_ip}\n"
    message += f"CPU Usage: {cpu_percent}%\n"
    message += f"RAM Usage: {ram_percent}%\n"
    message += f"Total Disk Space: {total_size}\n"
    message += f"Used Disk Space: {used_size}\n"
    message += f"Available Disk Space: {available_size}\n"
    message += f"Percentage Used: {percentage_used}\n"

    return message


if __name__ == "__main__":
    main()
