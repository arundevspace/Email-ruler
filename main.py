from clients.gmail_client import GmailClient
from data.data_manager import DBManager
from rules.rules_processor import RuleProcessor

def run_mail_processor():
    """
    Main function to run the email filtering logic.
    1. Initialize components.
    2. Fetch latest emails (to keep DB fresh).
    3. Load all emails from the database.
    4. Run the RuleProcessor against the emails.
    """
    print("--- Rule Mail Processor Started ---")
    
    # 1. Initialize Components
    try:
        db_manager = DBManager()
        gmail_client = GmailClient() # Authenticates here
    except Exception as e:
        print(f"Critical error during initialization: {e}")
        return

    # 2. Ingest Data (Optional: Run ingestion again to ensure fresh data)
    print("Step 2: Fetching latest emails to update local database...")
    emails_to_ingest = gmail_client.fetch_emails(max_results=50)
    for email in emails_to_ingest:
        db_manager.save_email(email)
    print(f"Ingested {len(emails_to_ingest)} emails.")


    # 3. Load all Emails from the DB for processing
    print("Step 3: Loading all emails from the database for rule execution...")
    all_emails = db_manager.get_all_emails()
    
    # 4. Initialize and Run Rule Processor
    # Pass the client and db manager to the processor so it can execute actions
    rule_processor = RuleProcessor(
        rules_file='rules/rules.json', 
        db_manager=db_manager, 
        gmail_client=gmail_client
    )
    
    print(f"Step 4: Executing rules on {len(all_emails)} emails.")
    rule_processor.process_emails(all_emails)
    
    # 5. Cleanup
    db_manager.close()
    print("--- Rule Mail Processor Finished ---")

if __name__ == '__main__':
    run_mail_processor()