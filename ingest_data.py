from clients.gmail_client import GmailClient
from data.data_manager import DBManager

def ingest_latest_emails(max_emails=100):
    """
    1. Authenticates with Gmail.
    2. Fetches the latest emails.
    3. Saves them to the SQLite database.
    """
    print("--- Starting Data Ingestion ---")
    
    # 1. Initialize Clients
    try:
        gmail_client = GmailClient()
        db_manager = DBManager()
    except Exception as e:
        print(f"Failed to initialize client or database: {e}")
        return

    # 2. Fetch Emails
    print(f"Fetching up to {max_emails} emails from Gmail...")
    # Avoid refetching messages already stored in the DB to save quota
    existing_ids = set(db_manager.get_all_ids())
    emails = gmail_client.fetch_emails(max_emails, existing_ids=existing_ids)
    
    if not emails:
        print("No emails fetched. Check API connection/permissions.")
        return

    # 3. Save to DB
    saved_count = 0
    print(f"Saving {len(emails)} emails to the database...")
    for email in emails:
        db_manager.save_email(email)
        saved_count += 1
    
    print(f"Data ingestion complete. Saved/Checked {saved_count} emails.")
    db_manager.close()

if __name__ == '__main__':
    # You will need to run this script once to populate your DB
    # Ensure you have 'client_secret.json' in the root directory before running!
    ingest_latest_emails(max_emails=50)