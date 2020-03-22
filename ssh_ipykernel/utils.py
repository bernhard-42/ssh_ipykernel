import logging
import os
import platform
import subprocess
from tornado.log import LogFormatter


if platform.system() == "Windows":
    is_windows = True
    SSH = "ssh.exe"
else:
    is_windows = False
    SSH = "ssh"


def setup_logging(name):
    """Setup Logging
    """
    _log_fmt = (
        "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d " "%(name)s]%(end_color)s %(message)s"
    )
    _log_datefmt = "%H:%M:%S"

    logger = logging.getLogger(name)
    debug_level = os.environ.get("DEBUG", "INFO")
    logger.setLevel(debug_level)
    logger.propagate = False
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(LogFormatter(fmt=_log_fmt, datefmt=_log_datefmt))
    logger.addHandler(console)
    return logger


logger = setup_logging("ssh_ipykernel:utils")


def execute(cmd):
    try:
        logger.debug("interrupt cmd = %s" % cmd)
        result = subprocess.check_output(cmd)
        result = {"code": 0, "data": result.decode("utf-8")}
    except subprocess.CalledProcessError as e:
        result = {"code": e.returncode, "data": e.args}

    logger.debug("result=%s", str(result))
    return result


def ssh(host, cmd):
    return execute([SSH, host, cmd])


def decode_utf8(s):
    if isinstance(s, str):
        return s
    elif isinstance(s, bytes):
        return s.decode("utf-8", "replace")
    else:
        raise ValueError("s is neither str nor bytes")
