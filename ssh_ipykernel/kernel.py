import json
import logging
import os
import platform
import re
import signal
import subprocess
import sys
import uuid

from jupyter_client import BlockingKernelClient
from tornado.log import LogFormatter

if platform.system() == "Windows":
    SSH = "ssh.exe"
    ENCODING = {"codepage": 65001}
    os.environ["WEXPECT_SPAWN_CLASS"] = "SpawnPipe"
    import wexpect as expect  # pylint: disable=import-error
else:
    SSH = "ssh"
    ENCODING = {"encoding": "utf-8"}
    import pexpect as expect  # pylint: disable=import-error

from .status import Status


# No tabs, no multiline, quote { and } !
KERNEL_SCRIPT = """
import json
import os
fname = os.path.expanduser("{fname}")
from jupyter_client import write_connection_file
write_connection_file(fname=fname, ip="{ip}", key=b"{key}", transport="{transport}", signature_scheme="{signature_scheme}", kernel_name="{kernel_name}")
fd = open(fname, "r")
ci = json.loads(fd.read())
fd.close()
ports = json.dumps({{k:v for k,v in ci.items() if "_port" in k}})
print(ports)
"""


class SshKernelException(Exception):
    pass


class SshKernel:
    """Remote ipykernel via SSH

    Raises:
        SshKernelException: "Could not execute remote command, connection died"
        SshKernelException: "Connection failed"
        SshKernelException: "Could not create kernel_info file"

        Arguments:
            host {str} -- host where the remote ipykernel should be started
            connection_info {dict} -- Local ipykernel connection info as provided by Juypter lab
            python_path {str} -- Remote python path to be used to start ipykernel

        Keyword Arguments:
            sudo {bool} -- Start ipykernel as root if necessary (default: {False})
            timeout {int} -- SSH connection timeout (default: {5})
            env {str} -- Environment variables passd to the ipykernel "VAR1=VAL1 VAR2=VAL2" (default: {""})
            ssh_config {List(str)} -- Path to the local SSH config file (default: {["~/" ".ssh", "config"]})
    """

    def __init__(
        self,
        host,
        connection_info,
        python_path,
        sudo=False,
        timeout=5,
        env="",
        ssh_config=None,
        quiet=True,
        verbose=False,
    ):
        self.host = host
        self.connection_info = connection_info
        self.python_path = python_path
        self.python_full_path = os.path.join(self.python_path, "bin/python")
        self.sudo = sudo
        self.timeout = timeout
        self.env = env
        if ssh_config is None:
            ssh_config = ["~/" ".ssh", "config"]
        self.ssh_config = os.path.join(*ssh_config)
        self.ssh_config = os.path.expanduser(self.ssh_config)
        self.quiet = quiet
        self.verbose = verbose

        self._connection = None

        self.remote_ports = {}
        self.uuid = str(uuid.uuid4())
        self.fname = "/tmp/.ssh_ipykernel_%s.json" % self.uuid

        self._setup_logging()
        self._logger.debug("Remote kernel info file {0}".format(self.fname))
        self._logger.debug(connection_info)

        self.status = Status(connection_info, self._logger)

    def _setup_logging(self):
        """Setup Logging
        """
        _log_fmt = (
            "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d "
            "%(name)s]%(end_color)s %(message)s"
        )
        _log_datefmt = "%H:%M:%S"

        self._logger = logging.getLogger("ssh_ipykernel")
        self._logger.setLevel("DEBUG")
        self._logger.propagate = False
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(LogFormatter(fmt=_log_fmt, datefmt=_log_datefmt))
        self._logger.addHandler(console)

    def _execute(self, cmd):
        try:
            result = subprocess.check_output(cmd)
            return 0, result
        except subprocess.CalledProcessError as e:
            return e.returncode, e.args

    def _ssh(self, cmd):
        return self._execute([SSH, self.host, cmd])

    def close(self):
        """Close pcssh connection
        """
        if self._connection is not None and self._connection.isalive():
            self._logger.debug("Closing ssh connection")
            self._connection.logout()

    def create_remote_connection_info(self):
        """Create a remote ipykernel connection info file
        Uses KERNEL_SCRIPT to execute jupyter_client.write_connection_file remotely to request remote ports.
        The remote ports will be returned as json and stored to built the SSH tunnels later.
        The pxssh connection will be closed at the end.

        Raises:
            SshKernelException: "Could not create kernel_info file"
        """
        self._logger.info("Creating remote connection info")
        script = KERNEL_SCRIPT.format(fname=self.fname, **self.connection_info)

        cmd = "{python} -c '{command}'".format(
            python=self.python_full_path, command="; ".join(script.strip().split("\n"))
        )

        result = self._ssh(cmd)
        self._logger.debug(result)
        if result[0] == 0:
            self.remote_ports = json.loads(result[1].decode("utf-8"))
            self._logger.debug(
                "Local ports  = %s"
                % {k: v for k, v in self.connection_info.items() if "_port" in k}
            )
            self._logger.debug("Remote ports = %s" % self.remote_ports)
        else:
            self.status.set_unreachable()
            raise SshKernelException("Could not create kernel_info file")

    def start_kernel_and_tunnels(self):
        """Start Kernels and SSH tunnels
        A new pxssh connection will be created that will
        - set up the necessary ssh tunnels between remote kernel ports and local kernel ports
        - start the ipykernel on the remote host
        """
        self._logger.info("Setting up ssh tunnels")

        ssh_tunnels = []
        for port_name in self.remote_ports.keys():
            ssh_tunnels += [
                "-L",
                "{local_port}:127.0.0.1:{remote_port}".format(
                    local_port=self.connection_info[port_name],
                    remote_port=self.remote_ports[port_name],
                ),
            ]

        self._logger.info("Starting remote kernel")

        # Build remote command
        sudo = "sudo " if self.sudo else ""
        env = "" if self.env is None else " ".join(self.env) + " "
        cmd = "{sudo}{env} {python} -m ipykernel_launcher -f {fname}".format(
            sudo=sudo, env=env, python=self.python_full_path, fname=self.fname
        )
        self._logger.debug(cmd)

        # Build ssh command with all flags and tunnels
        if self.quiet:
            args = ["-q"]
        elif self.verbose:
            args = ["-v"]
        else:
            args = []
        args += ["-t", "-F", self.ssh_config] + ssh_tunnels + [self.host, cmd]
        self._logger.debug(args)

        prompt = re.compile(r"\n")

        # Start the child process
        self._connection = expect.spawn(SSH, args=args, **ENCODING)

        # Wait for prompt
        self._connection.expect(prompt, timeout=5)

        # print the texts
        self._logger.info(self._connection.before.strip("\r\n"))
        kc = BlockingKernelClient()
        kc.load_connection_info(self.connection_info)
        kc.start_channels()
        alive = "alive" if kc.is_alive() else "NOT alive"
        self._logger.info("Remote kernel is {alive}".format(alive=alive))
        self.status.set_running()

        while True:
            try:
                # Wait for prompt
                self._connection.expect(prompt)
                # print the outputs
                self._logger.info(self._connection.before.strip("\r\n"))
            except KeyboardInterrupt:
                self._logger.warning("Received KeyboardInterrupt")
                if self._connection.isalive():
                    self._logger.info("Sending interrupt to remote kernel")
                    self._connection.sendintr()  # send SIGINT
                continue
            except expect.TIMEOUT:
                alive = "alive" if kc.is_alive() else "NOT alive"
                self._logger.debug("Remote kernel is {alive}".format(alive=alive))
            except expect.EOF:
                # The program has exited
                self._logger.info("The program has exited.")
                self.status.set_down()
                break

        self.close()
        self.status.close()
