# 🛠️ Unitus Project

Welcome to the Unitus project! This guide will walk you through the step-by-step process of setting up the project from scratch on your local machine. 

To ensure maximum security and best practices, this project uses a principle of least privilege for the database and environment variables to protect sensitive data[cite: 6].

---

## 📋 Prerequisites
Before you begin, ensure you have the following installed on your system:
* **Python** (v3.8 or higher)
* **MySQL Server**
* **Git**

---

## 🚀 Step-by-Step Setup Guide

### 1. Clone the Repository & Environment Setup
First, clone the project and set up an isolated Python virtual environment:

```bash
# Clone the repository
git clone <your-repository-url>
cd unitus-project-folder

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Mac/Linux:
source .venv/bin/activate

# Install all required dependencies
pip install -r requirements.txt

```

### 2. Database Creation & Security Roles

This project uses two separate MySQL users: an **Admin** (`db_admin`) for structural changes (migrations) and a **Backend User** (`app_backend`) for daily runtime operations.

Run the provided SQL script to automatically create the database and these users. Open your terminal in the root directory (where `setup_db_users.sql` is located) and run:

**For Windows (CMD):**

```cmd
mysql -u root -p < setup_db_users.sql

```

**For Windows (PowerShell) / Mac / Linux:**

```bash
mysql -u root -p -e "source setup_db_users.sql"

```

*(You will be prompted to enter your MySQL `root` password).*

### 3. Application Configuration

We keep our configuration files out of version control for security purposes. You need to create two files manually:

#### A. The `.env` File (Database Credentials)

Create a file named `.env` in the **root directory** of the project and add the standard backend user credentials:

```text
DEBUG=True
SECRET_KEY=your-django-secret-key
DB_NAME=unitus_db
DB_HOST=localhost
DB_PORT=3306

DB_ADMIN_USER=db_admin
DB_ADMIN_PASSWORD=YourAdminSecurePassword2026!

DB_APP_USER=app_backend
DB_APP_PASSWORD=YourAppSecurePassword2026!

```

#### B. The `local_setting.py` File (Django Settings)

Navigate to `unitus/unitus/` (where `settings.py` is located) and create a file named `local_setting.py` (or copy it from `local_setting.py.example` if available). Add the following content:

```python
# unitus/unitus/local_setting.py

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-custom-secret-key-here'

```

### 4. Apply Database Migrations

Since our daily database user (`app_backend`) does not have permission to alter table structures, we must temporarily use the `db_admin` credentials to apply migrations (which include custom triggers and data seeds).

We do this by injecting an environment variable `USE_ADMIN_DB=1` just for the migration command. Note that we do **not** need to run `makemigrations` because the migration files are already included in the repository.

**On Windows (PowerShell):**

```powershell
$env:USE_ADMIN_DB="1"
python unitus/manage.py migrate
$env:USE_ADMIN_DB=""

```

**On Windows (CMD):**

```cmd
set USE_ADMIN_DB=1
python unitus/manage.py migrate
set USE_ADMIN_DB=

```

**On Mac/Linux:**

```bash
USE_ADMIN_DB=1 python unitus/manage.py migrate

```

### 5. Run the Development Server

Everything is now configured! You can start the Django development server using the standard backend user (which happens automatically since we removed the admin flag):

```bash
python unitus/manage.py runserver

```

Open your browser and navigate to `http://127.0.0.1:8000/`. Welcome to Unitus! 🎉

```


```
## 🔍 Troubleshooting

### MySQL Error 1419 (SUPER privilege & binary logging)
If you encounter the following error while running the trigger migrations:
> `MySQLdb.OperationalError: (1419, 'You do not have the SUPER privilege and binary logging is enabled (you *might* want to use the less safe log_bin_trust_function_creators variable)')`

This happens because MySQL, by default, restricts user accounts from creating triggers or functions when binary logging is turned on. To safely bypass this on your local machine, follow these steps:

1. Open your terminal or database client and log into MySQL as the **root** user:
   ```bash
   mysql -u root -p

```

2. Execute the following global configuration command to trust function and trigger creators:
```sql
SET GLOBAL log_bin_trust_function_creators = 1;

```


3. Exit the MySQL prompt, return to your project terminal, and re-run the Django migration command:
```bash
# For PowerShell:
$env:USE_ADMIN_DB="1"; python unitus/manage.py migrate; $env:USE_ADMIN_DB=""

# For CMD:
set USE_ADMIN_DB=1 && python unitus/manage.py migrate && set USE_ADMIN_DB=

```
```

