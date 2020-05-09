import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import signal
import subprocess
import sys
import uuid

from jupyter_client import BlockingKernelClient
from tornado.log import LogFormatter

from ssh_ipykernel.utils import setup_logging

if platform.system() == "Windows":
    # os.environ["WEXPECT_SPAWN_CLASS"] = "SpawnPipe"
    import wexpect as expect  # pylint: disable=import-error

    # from wexpect.wexpect_util import SIGNAL_CHARS  # pylint: disable=import-error

    is_windows = True
    SSH = "ssh.exe"
    ENCODING = {"codepage": 65001}
    # SIGINT = SIGNAL_CHARS[signal.SIGINT]
else:
    import pexpect as expect  # pylint: disable=import-error

    is_windows = False
    SSH = "ssh"
    ENCODING = {"encoding": "utf-8"}
    # SIGINT = signal.SIGINT

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
            ssh_config {str} -- Path to the local SSH config file (default: {Path.home() / ".ssh" / "config"})
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
        msg_interval=30,
        logger=None,
    ):
        self.host = host
        self.connection_info = connection_info
        self.python_full_path = PurePosixPath(python_path) / "bin/python"
        self.sudo = sudo
        self.timeout = timeout
        self.env = env
        self.ssh_config = (
            Path.home() / ".ssh" / "config" if ssh_config is None else ssh_config
        )  # OS specific path

        self.quiet = quiet
        self.verbose = verbose

        self._connection = None

        self.remote_ports = {}
        self.uuid = str(uuid.uuid4())
        self.fname = "/tmp/.ssh_ipykernel_%s.json" % self.uuid  # POSIX path

        if logger is None:
            self._logger = setup_logging("SshKernel")
        else:
            self._logger = logger

        self._logger.debug("Remote kernel info file: {0}".format(self.fname))
        self._logger.debug("Local connection info: {0}".format(connection_info))

        self.kernel_pid = 0
        self.status = Status(connection_info, self._logger)
        self.msg_interval = int(msg_interval / timeout)
        self.msg_counter = 0

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
        if self._connection is not None:  # and self._connection.isalive():
            if self._connection.isalive():
                self._connection.logout()
                self._logger.debug("Ssh connection closed")
            if self.kc.is_alive():
                self.kc.stop_channels()
                self._logger.debug("Kernel client channels stopped")

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
            self.status.set_unreachable(self.kernel_pid, self.sudo)
            raise SshKernelException("Could not create kernel_info file")

    def kernel_client(self):
        self.kc = BlockingKernelClient()
        self.kc.load_connection_info(self.connection_info)
        self.kc.start_channels()

    def kernel_init(self):
        done = False
        if self.check_alive(show_pid=False):
            i = 0
            while not done:
                try:
                    i += 1
                    self._logger.debug("Retrieving kernel pid, attempt %d" % i)
                    result = self.kc.execute_interactive(
                        "import os",
                        user_expressions={"pid": "os.getpid()"},
                        store_history=False,
                        silent=True,
                        timeout=2,
                    )
                    self._logger.debug("result = %s" % str(result["content"]))
                    self.kernel_pid = int(
                        result["content"]["user_expressions"]["pid"]["data"]["text/plain"]
                    )
                    self._logger.debug("Remote kernel pid %d" % self.kernel_pid)
                    done = True
                except Exception as ex:
                    msg = str(ex)
                    if msg == "Timeout waiting for output":
                        self._logger.warning("Warning: {}".format(msg))
                        if i > 5:
                            self._logger.error("Max attempts (5) reached, stopping")
                            raise SshKernelException("Could not initialize kernel")
                            break
                    else:
                        self._logger.error("Warning: {}".format(str(ex)))
        return done

    def kernel_customize(self):
        pass

    def check_alive(self, show_pid=True):
        alive = self._connection.isalive() and self.kc.is_alive()
        if show_pid:
            msg = "Remote kernel ({}, pid = {}) is {}alive".format(
                self.host, self.kernel_pid, "" if alive else "not "
            )
        else:
            msg = "Remote kernel is {}alive".format("" if alive else "not ")

        if not alive or self.msg_counter % self.msg_interval == 0:
            self.msg_counter = 0
            self._logger.info(msg)

        self.msg_counter += 1
        return alive

    def interrupt_kernel(self):
        if self._connection.isalive():
            if is_windows:
                self._logger.warning('On Windows use "Interrupt remote kernel" button')
            else:
                self._logger.warning("Sending interrupt to remote kernel")
                self._connection.sendintr()  # send SIGINT

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

        if self.env is not None:
            env = " ".join(self.env)
        cmd = "{sudo} {env} {python} -m ipykernel_launcher -f {fname}".format(
            sudo=sudo, env=env, python=self.python_full_path, fname=self.fname
        )

        # Build ssh command with all flags and tunnels
        if self.quiet:
            args = ["-q"]
        elif self.verbose:
            args = ["-v"]
        else:
            args = []
        args += ["-t", "-F", str(self.ssh_config)] + ssh_tunnels + [self.host, cmd]

        self._logger.debug("%s %s" % (SSH, " ".join(args)))

        try:
            # Start the child process
            self._connection = expect.spawn(SSH, args=args, timeout=self.timeout, **ENCODING)
            # subprocess.check_output([SSH] + args)
            #
            # get blocking kernel client
            self.kernel_client()
            # initialize it
            if self.kernel_init():
                self.status.set_running(self.kernel_pid, self.sudo)
                # run custom code if part of sub class
                self.kernel_customize()
            else:
                self.status.set_connect_failed(sudo=self.sudo)
        except Exception as e:
            tb = sys.exc_info()[2]
            self._logger.error(str(e.with_traceback(tb)))
            self._logger.error("Cannot contiune, exiting")
            sys.exit(1)

        prompt = re.compile(r"\n")

        while True:
            try:
                # Wait for prompt
                self._connection.expect(prompt)
                # print the outputs
                self._logger.info(self._connection.before.strip("\r\n"))

            except KeyboardInterrupt:
                self.interrupt_kernel()
                self.check_alive()

            except expect.TIMEOUT:
                self.check_alive()

            except expect.EOF:
                # The program has exited
                self._logger.info("The program has exited.")
                self.status.set_down(self.kernel_pid, self.sudo)
                break

        self.close()
        self.status.close()
