from dataclasses import dataclass
from datetime import datetime

# Email data class used for standardization across the application and mapping to the DB
@dataclass(frozen=True)
class Email:
    id: str
    thread_id: str
    from_address: str
    subject: str
    body_text: str
    received_at: datetime
    is_read: bool