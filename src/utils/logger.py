import logging
from rich.logging import RichHandler
from rich.console import Console

console = Console()

def setup_logger(name="HorrorGen", level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    return logging.getLogger(name)

logger = setup_logger()
