import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_file="docsense.log", level=logging.INFO):
    root = logging.getLogger()
    
    if root.handlers:
        return root

    # Standardized format: 2026-02-09 20:25:00 [INFO] (backend.main) Message
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # File handler
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    
    root.setLevel(level)
    root.addHandler(file_handler)

    logging.info("Logging system standardized. Integrated with file and console.")
    return root