"""
Models package initialization.

Avoid importing submodules at package import time to prevent
circular import issues. Import specific symbols directly from
their modules where needed (e.g. `from models.email import Email`).
"""

__all__ = ["email"]