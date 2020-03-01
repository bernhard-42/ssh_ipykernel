import json
import logging
import os
import signal

from notebook.base.handlers import IPythonHandler
from tornado import web

from ssh_ipykernel.utils import ssh, setup_logging

logger = setup_logging("ssh_ipykernel:interrupt")


class SshInterruptHandler(IPythonHandler):
    """Kernel handler to interrupt remote ssh ipykernel"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @web.authenticated
    def get(self):
        """GET handler to interrrupt remote ssh ipykernel"""
        logger.warning("Interrupt remote kernel")
        pid = self.get_argument("pid", None, True)
        host = self.get_argument("host", None, True)
        cmd = "kill -{sig} {pid}".format(sig=signal.SIGINT.real, pid=pid)
        result = ssh(host, cmd)
        self.finish(json.dumps(result))


def _jupyter_server_extension_paths():
    """
    Set up the server extension for status handling
    """
    return [{"module": "ssh_ipykernel",}]
