import logging
import os

def setup_logging():
    directory = 'bot_log'
    if not os.path.exists(directory):
        os.mkdir(directory)

    filename = 'bot.log'

    filepath = os.path.join(directory, filename)
    file_handler = logging.FileHandler(filepath)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler]
    )
    
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.setLevel(logging.ERROR) 
    sqlalchemy_logger.addHandler(file_handler)
    sqlalchemy_logger.propagate = False 

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if not isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)
