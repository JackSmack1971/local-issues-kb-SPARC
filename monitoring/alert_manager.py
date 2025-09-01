import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class AlertManager:
    """Simple alert manager writing critical events to the log."""

    def __init__(self, *, enabled: Optional[bool] = None) -> None:
        env_enabled = os.getenv('ALERTS_ENABLED', 'true').lower() != 'false'
        self.enabled = env_enabled if enabled is None else enabled

    def critical(self, message: str) -> None:
        if not self.enabled:
            return
        if not isinstance(message, str) or not message:
            raise ValueError('message must be a non-empty string')
        logger.critical(message)
