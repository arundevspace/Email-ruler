import argparse
from clients.gmail_client import GmailClient
from data.data_manager import DBManager
from rules.rules_processor import RuleProcessor


def run_mail_processor(dry_run: bool = False, verbose: bool = False, rule_name: str = None, rule_index: int = None):
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
        gmail_client = None
        if not dry_run:
            gmail_client = GmailClient() # Authenticates here
    except Exception as e:
        print(f"Critical error during initialization: {e}")
        return

    # 2. Ingest Data (Optional: Run ingestion again to ensure fresh data)
    if not dry_run:
        print("Step 2: Fetching latest emails to update local database...")
        emails_to_ingest = gmail_client.fetch_emails(max_results=50)
        for email in emails_to_ingest:
            db_manager.save_email(email)
        print(f"Ingested {len(emails_to_ingest)} emails.")
    else:
        print("Step 2: Dry-run mode enabled — skipping Gmail ingestion.")


    # 3. Load all Emails from the DB for processing
    print("Step 3: Loading all emails from the database for rule execution...")
    all_emails = db_manager.get_unprocessed_emails()
    
    # 4. Initialize and Run Rule Processor
    # Pass the client and db manager to the processor so it can execute actions
    rule_processor = RuleProcessor(
        rules_file='rules/rules.json', 
        db_manager=db_manager, 
        gmail_client=gmail_client,
        dry_run=dry_run,
        verbose=verbose
    )

    # If a specific rule was requested, filter the loaded rules accordingly
    if rule_name:
        matched = [r for r in rule_processor.rules if rule_name.lower() in r.description.lower()]
        if not matched:
            print(f"No rules found matching '{rule_name}'. Available rules:")
            for i, r in enumerate(rule_processor.rules):
                print(f"  {i}: {r.description}")
            db_manager.close()
            return
        rule_processor.rules = matched
        print(f"Filtered to {len(matched)} rule(s) matching '{rule_name}'")
    elif rule_index is not None:
        if rule_index < 0 or rule_index >= len(rule_processor.rules):
            print(f"Rule index {rule_index} out of range (0..{len(rule_processor.rules)-1})")
            db_manager.close()
            return
        rule_processor.rules = [rule_processor.rules[rule_index]]
        print(f"Filtered to rule index {rule_index}: '{rule_processor.rules[0].description}'")
    
    print(f"Step 4: Executing rules on {len(all_emails)} emails.")
    print("Rules to apply:")
    for i, r in enumerate(rule_processor.rules):
        print(f"  {i}: {r.description}")
    rule_processor.process_emails(all_emails)
    
    # 5. Cleanup
    db_manager.close()
    print("--- Rule Mail Processor Finished ---")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the email rule processor')
    parser.add_argument('--dry-run', action='store_true', help='Do not call Gmail API; just print actions')
    parser.add_argument('--verbose', action='store_true', help='Show per-email condition evaluations')
    parser.add_argument('--rule', type=str, help='Run only rules whose description contains this string (case-insensitive)')
    parser.add_argument('--rule-index', type=int, help='Run only the rule at this 0-based index')
    args = parser.parse_args()
    run_mail_processor(dry_run=args.dry_run, verbose=args.verbose, rule_name=args.rule, rule_index=args.rule_index)