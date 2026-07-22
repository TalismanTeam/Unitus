CREATE DATABASE IF NOT EXISTS unitus_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

DROP USER IF EXISTS 'db_admin'@'localhost';
DROP USER IF EXISTS 'app_backend'@'localhost';

-- replace your own passwords from .env
CREATE USER 'db_admin'@'localhost' IDENTIFIED BY '0907';
CREATE USER 'app_backend'@'localhost' IDENTIFIED BY '0907';

GRANT ALL PRIVILEGES ON unitus_db.* TO 'db_admin'@'localhost';
GRANT ALL PRIVILEGES ON unitus_db.* TO 'app_backend'@'localhost';

FLUSH PRIVILEGES;