import logging
import logging.handlers
import os


def configure_logging(level=logging.WARNING, log_dir=None, debug_mode=False):
    if debug_mode:
        level = logging.DEBUG
    root = logging.getLogger()
    root.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "krakensdr_doa.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
