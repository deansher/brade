import sys
import logging
import aider
from aider.main import main as aider_main

# Configure logging
logger = logging.getLogger(__name__)


def main():
    logger.debug("Executing brade's main entry point.")
    logger.debug(f"Using aider module from: {aider.__file__}")
    return aider_main()


if __name__ == "__main__":
    status = main()
    sys.exit(status)
