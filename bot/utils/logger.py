"""Structured logging for the bot."""
import logging
import sys
from bot.config import LOG_LEVEL


class DashboardLogHandler(logging.Handler):
    """Custom handler that sends logs to dashboard state for real-time display."""
    
    def __init__(self):
        super().__init__()
        self.dashboard_state = None
        
    def set_dashboard_state(self, dashboard_state):
        """Set dashboard state reference."""
        self.dashboard_state = dashboard_state
        
    def emit(self, record):
        """Send log record to dashboard state."""
        if self.dashboard_state:
            try:
                # Format the message like terminal output
                msg = self.format(record)
                level = record.levelname.lower()
                
                # Send to dashboard state
                self.dashboard_state.add_log(msg, level=level)
            except Exception:
                # Don't let logging errors break the application
                pass


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
            
        # Terminal handler (original)
        terminal_handler = logging.StreamHandler(sys.stdout)
        terminal_fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-7s %(name)-25s | %(message)s",
            datefmt="%H:%M:%S",
        )
        terminal_handler.setFormatter(terminal_fmt)
        logger.addHandler(terminal_handler)
        
        # Dashboard handler (new)
        dashboard_handler = DashboardLogHandler()
        dashboard_fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-7s %(name)-25s | %(message)s",
            datefmt="%H:%M:%S",
        )
        dashboard_handler.setFormatter(dashboard_fmt)
        logger.addHandler(dashboard_handler)
        
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    return logger


def setup_dashboard_logging(dashboard_state):
    """Setup dashboard logging by injecting dashboard state into all handlers."""
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            if isinstance(handler, DashboardLogHandler):
                handler.set_dashboard_state(dashboard_state)


def sanitize_reason_for_ui(reason: str) -> str:
    """
    Sanitize action reasoning to hide strategy details from other players.
    Local logs keep full reasoning, but UI gets generic messages.
    """
    # Generic action descriptions that don't reveal strategy
    generic_actions = [
        "Exploring area",
        "Moving position", 
        "Searching for items",
        "Resting",
        "Using item",
        "Equipping gear",
        "Attacking target",
        "Picking up item",
        "Interacting with facility"
    ]
    
    # Map specific reasons to generic ones
    reason_lower = reason.lower()
    
    if any(word in reason_lower for word in ["heal", "hp", "health", "critical"]):
        return "Using item"
    elif any(word in reason_lower for word in ["move", "flee", "escape", "run"]):
        return "Moving position"
    elif any(word in reason_lower for word in ["attack", "fight", "combat", "kill"]):
        return "Attacking target"
    elif any(word in reason_lower for word in ["pickup", "collect", "take"]):
        return "Picking up item"
    elif any(word in reason_lower for word in ["equip", "weapon", "gear"]):
        return "Equipping gear"
    elif any(word in reason_lower for word in ["rest", "ep", "energy"]):
        return "Resting"
    elif any(word in reason_lower for word in ["interact", "facility", "cache"]):
        return "Interacting with facility"
    else:
        return "Exploring area"
