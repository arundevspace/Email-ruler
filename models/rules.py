from dataclasses import dataclass
from typing import List, Dict, Any

# Represents a single action (e.g., Mark as Read, Move Message)
@dataclass(frozen=True)
class Action:
    type: str   # e.g., "Mark as Read", "Move Message"
    value: str = None # e.g., "UNREAD" or "Processed" (mailbox name)

# Represents a single condition (e.g., From, contains)
@dataclass(frozen=True)
class Condition:
    field: str      # e.g., "From", "Subject", "Received Date/Time"
    operator: str   # e.g., "contains", "less than (days)", "equals"
    value: str      # The target value for comparison

# Represents an entire rule set
@dataclass(frozen=True)
class Rule:
    description: str
    predicate: str                      # "All" or "Any"
    conditions: List[Condition]         # List of conditions to check
    actions: List[Action]               # List of actions to perform