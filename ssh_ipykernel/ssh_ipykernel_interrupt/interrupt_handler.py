import json
import os
import signal

from notebook.base.handlers import IPythonHandler
from tornado import web

from ssh_ipykernel.utils import ssh, setup_logging

from ssh_ipykernel.status import Status

logger = setup_logging("ssh_ipykernel:interrupt")


class SshInterruptHandler(IPythonHandler):
    """Kernel handler to interrupt remote ssh ipykernel"""

    nbapp = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_kernel(self, kernel_id):
        """Get jupyter kernel for given kernel Id
        
        Args:
            kernel_id (str): Internal jupyter kernel ID
        
        Returns:
            KernelManager: KernelManager object
        """
        km = SshInterruptHandler.nbapp.kernel_manager

        kernel_info = None
        for kernel_info in km.list_kernels():
            if kernel_info["id"] == kernel_id:
                break

        if kernel_info is not None:
            return km.get_kernel(kernel_info["id"])
        else:
            return None

    @web.authenticated
    def get(self):
        """GET handler to interrrupt remote ssh ipykernel"""

        kernel_id = self.get_argument("id", None, True)
        logger.debug("kernel id %s" % kernel_id)
        kernel = self.get_kernel(kernel_id)

        status = Status(kernel.get_connection_info(), logger)
        if status.is_running():
            pid = status.get_pid()

            host = ""
            for i, v in enumerate(kernel.kernel_spec.argv):
                if v == "--host":
                    host = kernel.kernel_spec.argv[i + 1]
                    break

            logger.warning("Interrupt remote kernel ({}, pid = {})".format(host, pid))

            cmd = "kill -{sig} {pid}".format(sig=signal.SIGINT.real, pid=pid)
            if status.is_sudo():
                cmd = "sudo " + cmd
            result = ssh(host, cmd)
        else:
            result = {"code": -1, "data": "Remote kernel not running"}

        self.finish(json.dumps(result))


def _jupyter_server_extension_paths():
    """
    Set up the server extension for status handling
    """
    return [{"module": "ssh_ipykernel",}]
