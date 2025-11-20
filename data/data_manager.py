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
        # Ensure 'processed' column exists for tracking rule execution
        cursor.execute("PRAGMA table_info(emails)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'processed' not in cols:
            try:
                cursor.execute("ALTER TABLE emails ADD COLUMN processed INTEGER DEFAULT 0")
                self.conn.commit()
                print("Added 'processed' column to emails table.")
            except Exception:
                # If unable to alter (older sqlite), ignore and continue
                pass

    def save_email(self, email: Email):
        """Inserts a new email or ignores if it already exists."""
        # Convert datetime to UNIX timestamp (seconds since epoch) for storage
        received_at_timestamp = email.received_at.timestamp()
        is_read_int = 1 if email.is_read else 0

        INSERT_SQL = """
        INSERT OR IGNORE INTO emails 
        (id, thread_id, from_address, subject, received_at, body_text, is_read, processed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = (
            email.id, email.thread_id, email.from_address,
            email.subject, received_at_timestamp, email.body_text,
            is_read_int, 0
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
            # Handle possible schema differences: processed column may be at index 7
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

    def get_unprocessed_emails(self) -> List[Email]:
        """Retrieve emails that haven't been processed by rules yet."""
        SELECT_SQL = "SELECT * FROM emails WHERE processed IS NULL OR processed = 0"
        cursor = self.conn.cursor()
        cursor.execute(SELECT_SQL)
        rows = cursor.fetchall()

        emails = []
        for row in rows:
            received_dt = datetime.fromtimestamp(row[4])
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

    def get_all_ids(self) -> List[str]:
        """Return a list of all stored message IDs."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM emails")
        rows = cursor.fetchall()
        return [r[0] for r in rows]

    def mark_processed(self, email_id: str):
        """Mark an email as processed so it won't be reprocessed."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE emails SET processed = 1 WHERE id = ?", (email_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error marking email {email_id} as processed: {e}")

    def reset_processed(self, email_id: str):
        """Mark a specific email as unprocessed (processed = 0)."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE emails SET processed = 0 WHERE id = ?", (email_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error resetting processed for {email_id}: {e}")

    def reset_all_processed(self):
        """Mark all emails as unprocessed (processed = 0)."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE emails SET processed = 0")
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error resetting processed for all emails: {e}")

    def reset_processed_older_than(self, days: int):
        """Reset processed flag for emails older than given days.

        This uses the stored UNIX timestamp in `received_at`.
        """
        threshold = datetime.now().timestamp() - (days * 24 * 3600)
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE emails SET processed = 0 WHERE received_at < ?", (threshold,))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error resetting processed for emails older than {days} days: {e}")

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