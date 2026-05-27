import logging

logger = logging.getLogger("messenger")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler()

logger.addHandler(handler)
handler.setFormatter(formatter)

