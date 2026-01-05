import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    log = logging.getLogger(name)
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log
