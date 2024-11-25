import logging
from scripts.data_preparation import create_index

if __name__ == "__main__":
    # TODO: handle command line arguments
    logging.getLogger().setLevel(logging.INFO)
    logging.info("MAIN: create_index")
    create_index()
