import src.utilities.logger as logger
import logging
import sys

if __name__ == "__main__":
    
    main_logger = logging.getLogger("Nelliel")
    main_logger.setLevel(getattr(logging, 'INFO'))
    console_handler = logging.StreamHandler(sys.stdout)
    general_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(general_format)
    main_logger.addHandler(console_handler)


    child_logger = logging.getLogger("Nelliel.Child")
    child_logger.setLevel(getattr(logging, "INFO"))
    child_handler = logging.StreamHandler(sys.stdout)
    format = logging.Formatter('%(message)s')
    child_handler.setFormatter(format)
    child_logger.addHandler(child_handler)
    child_logger.propagate = False

    child_logger.info("Test1")
    main_logger.info("Test2")