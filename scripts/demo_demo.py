from datetime import datetime, timezone
import sys

from models.email import Email
from rules.rules_processor import RuleProcessor


def make_demo_email():
    # Construct an email that will match the Linked Job Alerts rule
    return Email(
        id='demo-1',
        thread_id='demo-thread',
        from_address='jobalerts-noreply@linkedin.com',
        subject='python developer role - demo',
        body_text='This is a demo job alert message containing developer and python.',
        received_at=datetime.now(timezone.utc),
        is_read=False
    )


def run_demo():
    email = make_demo_email()
    # Use dry_run and verbose so the actions are printed but not sent
    processor = RuleProcessor(rules_file='rules/rules.json', db_manager=None, gmail_client=None, dry_run=True, verbose=True)
    processor.process_emails([email])


if __name__ == '__main__':
    try:
        run_demo()
    except Exception as e:
        print('Demo failed:', e)
        sys.exit(1)