import json
import os
import re
from datetime import datetime, timedelta
from typing import List

# Import dataclasses from the local models package
from models.rules import Rule, Condition, Action
from models.email import Email
from clients.gmail_client import GmailClient  # Needed for action execution

class RuleProcessor:
    def __init__(self, rules_file='rules/rules.json', db_manager=None, gmail_client=None):
        # Load rules only if a rules_file path is provided; allow tests to inject rules directly
        if rules_file:
            self.rules: List[Rule] = self._load_rules(rules_file)
        else:
            self.rules: List[Rule] = []
        self.db = db_manager # For potential DB updates
        self.client = gmail_client # For API actions

    def _load_rules(self, file_path) -> List[Rule]:
        """Loads and parses the JSON rules file into Rule objects."""
        if not os.path.exists(file_path):
            print(f"Error: Rules file not found at {file_path}")
            return []
        
        with open(file_path, 'r') as f:
            data = json.load(f)

        rules = []
        for rule_data in data:
            conditions = [Condition(**c) for c in rule_data['conditions']]
            actions = [Action(**a) for a in rule_data['actions']]
            
            rules.append(Rule(
                description=rule_data['description'],
                predicate=rule_data['predicate'],
                conditions=conditions,
                actions=actions
            ))
        return rules

    def _check_condition(self, email: Email, condition: Condition) -> bool:
        """
        Evaluates a single condition against the email. This is the core logic.
        Implements all required string and date predicates (Less than/Greater than).
        """
        field_name = condition.field.lower()
        operator = condition.operator.lower()
        value = condition.value
        
        # 1. Determine the email field value to check
        if field_name == 'from':
            email_value = email.from_address
        elif field_name == 'subject':
            email_value = email.subject
        elif field_name == 'message':
            email_value = email.body_text
        elif field_name == 'received date/time':
            email_value = email.received_at
        else:
            return False # Field not supported

        # 2. Perform comparison based on operator
        
        # String Comparisons: From, Subject, Message [cite: 52]
        if operator == 'contains':
            return value.lower() in email_value.lower()
        elif operator == 'does not contain':
            return value.lower() not in email_value.lower()
        elif operator == 'equals':
            return value.lower() == email_value.lower()
        elif operator == 'does not equal':
            return value.lower() != email_value.lower()

        # Date Comparisons: Received Date/Time [cite: 53]
        elif field_name == 'received date/time':
            now = datetime.now(email_value.tzinfo) # Use same timezone for safety
            
            # Extract unit and magnitude from operator (e.g., 'less than (days)')
            match = re.search(r'\((\w+)\)', operator)
            unit = match.group(1) if match else 'days' # Default to days
            magnitude = int(value)
            
            # Calculate the threshold datetime
            if unit == 'days':
                threshold = timedelta(days=magnitude)
            elif unit == 'months':
                # Approximate 30 days per month for simplicity in a standalone script
                threshold = timedelta(days=magnitude * 30) 
            else:
                return False

            if 'less than' in operator:
                # Check if email is newer than the threshold
                return (now - email_value) < threshold
            elif 'greater than' in operator:
                # Check if email is older than the threshold
                return (now - email_value) > threshold

        return False

    def process_emails(self, emails: List[Email]):
        """Main loop to apply all loaded rules to a list of emails."""
        if not self.client:
            raise ValueError("Gmail Client must be set on RuleProcessor to perform actions.")
            
        print(f"\n--- Starting Rule Processing on {len(emails)} emails ---")

        for email in emails:
            # Check only unread emails to avoid modifying processed messages repeatedly
            # Optional: Process all emails if rules should run on read ones too.
            # if email.is_read:
            #     continue 

            is_rule_matched = False
            for rule in self.rules:
                match_results = [self._check_condition(email, condition) 
                                 for condition in rule.conditions]
                
                # Apply the overall predicate: "All" or "Any" [cite: 46, 47, 48]
                is_satisfied = False
                if rule.predicate.lower() == 'all':
                    is_satisfied = all(match_results)
                elif rule.predicate.lower() == 'any':
                    is_satisfied = any(match_results)

                if is_satisfied:
                    print(f"Rule MATCHED: '{rule.description}' for email ID: {email.id[:8]}...")
                    self._execute_actions(email, rule.actions)
                    is_rule_matched = True
                    # Optionally, break after the first match to prevent multiple rules from running
                    # on the same email (common filtering practice).
                    break

            if not is_rule_matched:
                pass # Email did not match any rule

    def _execute_actions(self, email: Email, actions: List[Action]):
        """Executes the list of actions via the GmailClient and updates the DB."""
        for action in actions:
            action_type = action.type.lower()

            if action_type == 'mark as read':
                if self.client.mark_as_read_unread(email.id, mark_as_read=True):
                    if self.db:
                        self.db.update_email_status(email.id, is_read=True)
            elif action_type == 'mark as unread':
                if self.client.mark_as_read_unread(email.id, mark_as_read=False):
                    if self.db:
                        self.db.update_email_status(email.id, is_read=False)
            elif action_type == 'move message':
                mailbox = action.value  # The target label/mailbox name
                if self.client.move_message(email.id, mailbox):
                    # Note: DB status update for move is optional; print for visibility
                    print(f"Action: Moved email {email.id[:8]}... to '{mailbox}'")