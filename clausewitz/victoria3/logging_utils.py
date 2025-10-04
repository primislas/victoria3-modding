import logging


# Simple colorizer for console logs
class _ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",    # Cyan
        logging.INFO: "\033[32m",     # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",    # Red
        logging.CRITICAL: "\033[41m", # Red background
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str, use_color: bool = True):
        super().__init__(fmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if self.use_color:
            color = self.COLORS.get(record.levelno)
            if color:
                return f"{color}{msg}{self.RESET}"
        return msg


def get_logger(name: str = "vicky3", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured (avoid duplicate handlers)
    active_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(active_level)
    handler = logging.StreamHandler()
    fmt = "[%(asctime)s][%(levelname)s] %(message)s"
    handler.setFormatter(_ColorFormatter(fmt=fmt, use_color=True))
    logger.addHandler(handler)
    return logger
