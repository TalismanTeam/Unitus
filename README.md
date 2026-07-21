## 🛠️ Project Setup and Database Configuration

To ensure project security, sensitive information such as database credentials and the Django secret key are excluded from the source code. Instead, we utilize environment variables via a `.env` file.

### Prerequisites
1. Ensure your virtual environment (`.venv`) is activated and install the required dependencies:

```bash
pip install -r requirements.txt
```

### Steps to Set Up Environment Variables and Database

#### 1. Create a Local Configuration File
In the root directory of the project, duplicate the `.env.example` file and rename it to `.env`:
* **Note:** The `.env` file remains strictly on your local machine and is safely ignored by Git (`.gitignore`).

#### 2. Configure Your Database Credentials
Open the newly created `.env` file and fill in your local MySQL database details:

```text
DB_NAME=unitus_db
DB_USER=your_local_database_user
DB_PASSWORD=your_local_database_password
DB_HOST=localhost
DB_PORT=3306
```

#### 3. Apply Database Migrations
Once the `.env` file is configured, run the following commands to apply the database schema:

```bash
python unitus/manage.py makemigrations
python unitus/manage.py migrate
```