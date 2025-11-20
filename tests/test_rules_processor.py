import sys
import pathlib
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

# Ensure the project root is on sys.path so tests can import local packages
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.email import Email
from models.rules import Rule, Condition, Action
from rules.rules_processor import RuleProcessor


def make_email(from_addr="alice@example.com", subject="Hello", body="Hi", days_ago=0, is_read=False):
    received_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return Email(id="msg1", thread_id="t1", from_address=from_addr, subject=subject, body_text=body, received_at=received_at, is_read=is_read)


def test_contains_condition_matches():
    rule = Rule(description="from contains example", predicate="All",
                conditions=[Condition(field="From", operator="contains", value="example.com")],
                actions=[Action(type="Mark as Read")])

    email = make_email(from_addr="bob@example.com")

    rp = RuleProcessor(rules_file=None, db_manager=Mock(), gmail_client=Mock())
    # inject rule directly
    rp.rules = [rule]

    # run processing; should call mark_as_read
    rp._execute_actions = Mock()
    rp.process_emails([email])

    rp._execute_actions.assert_called_once()


def test_predicate_any_all_logic():
    # rule with predicate Any: should match if any condition true
    r_any = Rule(description="any test", predicate="Any",
                 conditions=[
                     Condition(field="From", operator="contains", value="nomatch.com"),
                     Condition(field="Subject", operator="contains", value="Hello")
                 ],
                 actions=[])

    # rule with predicate All: should require both true
    r_all = Rule(description="all test", predicate="All",
                 conditions=[
                     Condition(field="From", operator="contains", value="example.com"),
                     Condition(field="Subject", operator="contains", value="Hello")
                 ],
                 actions=[])

    email = make_email(from_addr="bob@example.com", subject="Hello World")

    rp = RuleProcessor(rules_file=None, db_manager=None, gmail_client=Mock())
    rp.rules = [r_any, r_all]

    # verify the internal check behavior for each rule
    matches_any = [rp._check_condition(email, c) for c in r_any.conditions]
    assert any(matches_any)

    matches_all = [rp._check_condition(email, c) for c in r_all.conditions]
    assert all(matches_all)


def test_date_condition_less_than_days():
    # Match emails within last 3 days
    r = Rule(description="recent", predicate="All",
             conditions=[Condition(field="Received Date/Time", operator="less than (days)", value="3")],
             actions=[])

    email_recent = make_email(days_ago=1)
    email_old = make_email(days_ago=10)

    rp = RuleProcessor(rules_file=None, db_manager=None, gmail_client=Mock())
    rp.rules = [r]

    assert rp._check_condition(email_recent, r.conditions[0]) is True
    assert rp._check_condition(email_old, r.conditions[0]) is False


def test_execute_actions_calls_client_and_db():
    db = Mock()
    client = Mock()
    client.mark_as_read_unread.return_value = True
    client.move_message.return_value = True

    email = make_email()
    actions = [Action(type="Mark as Read"), Action(type="Move Message", value="Processed")]

    rp = RuleProcessor(rules_file=None, db_manager=db, gmail_client=client)
    rp._execute_actions(email, actions)

    client.mark_as_read_unread.assert_called_once_with(email.id, mark_as_read=True)
    client.move_message.assert_called_once_with(email.id, "Processed")
    db.update_email_status.assert_called_once_with(email.id, is_read=True)
