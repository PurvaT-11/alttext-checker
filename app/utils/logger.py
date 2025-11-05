import logging

def setup_logger():
    logger = logging.getLogger("alttext_checker")
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler("app.log")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(handler)

    return logger
