import sqlite3
from datetime import datetime
import time 
from typing import List

from models.email import Email

class DBManager:
    def __init__(self, db_name='email_data.db'):
        self.db_name = db_name
        self.conn = None
        self.connect()
        self.initialize_db()

    def connect(self):
        """Establishes the connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_name)
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise

    def initialize_db(self):
        """Creates the 'emails' table if it doesn't already exist."""
        # Using REAL (UNIX timestamp) for easier date comparisons
        CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            thread_id TEXT,
            from_address TEXT,
            subject TEXT,
            received_at REAL,
            body_text TEXT,
            is_read INTEGER
        );
        """
        cursor = self.conn.cursor()
        cursor.execute(CREATE_TABLE_SQL)
        self.conn.commit()
        print("Database schema ensured.")

    def save_email(self, email: Email):
        """Inserts a new email or ignores if it already exists."""
        # Convert datetime to UNIX timestamp (seconds since epoch) for storage
        received_at_timestamp = email.received_at.timestamp()
        is_read_int = 1 if email.is_read else 0

        INSERT_SQL = """
        INSERT OR IGNORE INTO emails 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        data = (
            email.id, email.thread_id, email.from_address, 
            email.subject, received_at_timestamp, email.body_text, 
            is_read_int
        )
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(INSERT_SQL, data)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error saving email {email.id}: {e}")

    def get_all_emails(self) -> List[Email]:
        """Retrieves all emails, converting DB rows back to Email dataclasses."""
        SELECT_SQL = "SELECT * FROM emails"
        cursor = self.conn.cursor()
        cursor.execute(SELECT_SQL)
        rows = cursor.fetchall()

        emails = []
        for row in rows:
            # Convert UNIX timestamp back to datetime object
            received_dt = datetime.fromtimestamp(row[4])
            # Convert integer back to boolean
            is_read_bool = bool(row[6])

            email = Email(
                id=row[0], 
                thread_id=row[1], 
                from_address=row[2], 
                subject=row[3],
                body_text=row[5], 
                received_at=received_dt, 
                is_read=is_read_bool
            )
            emails.append(email)
        return emails

    def update_email_status(self, email_id: str, is_read: bool, new_label: str = None):
        """Updates the local database status after a successful API action."""
        is_read_int = 1 if is_read else 0
        
        UPDATE_SQL = """
        UPDATE emails SET is_read = ? WHERE id = ?
        """
        
        cursor = self.conn.cursor()
        cursor.execute(UPDATE_SQL, (is_read_int, email_id))
        self.conn.commit()
        # Note: Moving an email is often a label change on the API side,
        # but for the local DB, we primarily track the read status.

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()