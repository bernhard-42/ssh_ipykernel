import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
import uuid

import pexpect
from pexpect import pxssh
from tornado.log import LogFormatter


class SshKernelException(Exception):
    pass


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


class SshKernel:
    def __init__(self, host, connection_info, python_path, sudo=False, timeout=5, env="", ssh_config="~/.ssh/config"):
        self.host = host
        self.connection_info = connection_info
        self.python_path = python_path
        self.python_full_path = os.path.join(self.python_path, "bin/python")
        self.sudo = sudo
        self.timeout = timeout
        self.env = env
        self.ssh_config = os.path.expanduser(ssh_config)
        self._connection = None

        self.remote_ports = {}
        self.uuid = str(uuid.uuid4())
        self.fname = "/tmp/.ssh_ipykernel_%s.json" % self.uuid

        self._setup_logging()
        self._logger.debug("Remote kernel info file {0}".format(self.fname))

        signal.signal(signal.SIGQUIT, self._quit_handler)
        signal.signal(signal.SIGINT, self._int_handler)

    def _quit_handler(self, signum, frame):
        self._logger.warning("Received SIGQUIT")
        if self._connection.isalive():
            self._logger.info("Sending quit to remote kernel")
            self._connection.sendcontrol("\\")  # sends SIGQUIT
            self._logger.debug("Remote kernel stopped")
            self._logger.info("Stopping ssh connection")
            self._connection.logout()

    def _int_handler(self, signum, frame):
        self._logger.warning("Received SIGINT")
        if self._connection.isalive():
            self._logger.info("Sending interrupt to remote kernel")
            self._connection.sendintr()  # send SIGINT

    def _setup_logging(self):
        _log_fmt = ("%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d " "%(name)s]%(end_color)s %(message)s")
        _log_datefmt = "%H:%M:%S"

        self._logger = logging.getLogger("ssh_ipykernel")
        self._logger.setLevel("DEBUG")
        self._logger.propagate = False
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(LogFormatter(fmt=_log_fmt, datefmt=_log_datefmt))
        self._logger.addHandler(console)

    def _decode_utf8(self, text):
        if isinstance(text, str):
            return text
        else:
            return text.decode("utf", "replace")

    def _get_result(self, result):
        return self._decode_utf8(result).split("\r\n")[1:]

    def _cmd(self, cmd):
        self._connection.sendline(cmd)
        while True:
            if self._connection.prompt():
                # prompt detected
                return self._get_result(self._connection.before)
            else:
                # timeout reached
                time.sleep(0.5)

    def _execute(self, cmd):
        if self._connection is not None and self._connection.isalive():
            result = self._cmd(cmd)
            returncode = self._cmd("echo $?")[0]
            try:
                returncode = int(returncode)
            except:
                self._logger.error("wrong returncode %s", returncode)
            return (returncode, result)
        else:
            raise SshKernelException("Could not execute remote command, connection died")

    def connect(self, retries=3, delay=5, ssh_tunnels=None):
        if ssh_tunnels is None:
            ssh_tunnels = {}
            msg = "Connected to host '%s'" % self.host
        else:
            msg = "Connected to host '%s' and create %d tunnels" % (self.host, len(ssh_tunnels["local"]))

        for dummy in range(retries):
            try:
                connection = pxssh.pxssh(timeout=self.timeout)
                connection.options = dict(
                    StrictHostKeyChecking="no",
                    ServerAliveCountMax=2,
                    ServerAliveInterval=self.timeout
                )
                connection.login(self.host, username=None, ssh_config=self.ssh_config, ssh_tunnels=ssh_tunnels)
                self._connection = connection
                self._logger.info(msg)
                break
            except Exception as e:
                self._logger.error("Failed to open connection")
                self._logger.error(e)
                self._logger.error("Waiting for %ds" % delay)
                time.sleep(5)

        if self._connection is None:
            raise SshKernelException("Connection failed")

    def close(self):
        if self._connection is not None and self._connection.isalive():
            self._logger.debug("Closing ssh connection")
            self._connection.logout()

    def create_remote_connection_info(self):
        self._logger.info("Creating remote connection info")
        # Create a remote kernel_info file
        script = KERNEL_SCRIPT.format(fname=self.fname, **self.connection_info)

        cmd = "{python} -c '{command}'".format(python=self.python_full_path,
                                               command="; ".join(script.strip().split("\n")))
        self.connect()
        result = self._execute(cmd)
        if result[0] == 0:
            self.remote_ports = json.loads(result[1][0])
            self._logger.debug("Remote ports = %s" % self.remote_ports)
        else:
            raise SshKernelException("Could not create kernel_info file")
        self.close()

    def start_kernel_and_tunnels(self):
        self._logger.info("Starting ipykernel on the remote server and setting up ssh tunnels")
        ssh_tunnels = {"local": []}
        for port_name in self.remote_ports.keys():
            ssh_tunnels["local"].append("127.0.0.1:{local_port}:127.0.0.1:{remote_port}".format(
                local_port=self.connection_info[port_name], remote_port=self.remote_ports[port_name]))
        self._logger.info("Starting remote kernel ...")
        sudo = "sudo " if self.sudo else ""
        env = "" if self.env is None else " ".join(self.env) + " "
        cmd = "{sudo}{env}{python} -m ipykernel_launcher -f {fname}".format(env=env,
                                                                            sudo=sudo,
                                                                            python=self.python_full_path,
                                                                            fname=self.fname)
        self._logger.debug(cmd)

        self.connect(ssh_tunnels=ssh_tunnels)
        self._connection.sendline(cmd)
        self._logger.info("Remote kernel started")

        while True:
            try:
                result = self._connection.prompt()
                if result:
                    # ssh prompt detected, so the kernel died
                    self._logger.error(self._decode_utf8(self._connection.before))
                    break
                else:
                    # timeout reached
                    if self._connection.before != b'':
                        # print the buffer - it is just some kernel output
                        lines = self._get_result(self._connection.before)
                        for line in lines:
                            self._logger.info(line)
                        # and clear what we have printed
                        self._connection.buffer = b''
                        self._connection.before = b''

                time.sleep(self.timeout)
            except pexpect.EOF:
                lines = self._get_result(self._connection.before)
                for line in lines:
                    self._logger.info(line)
                break
        self._logger.error("Kernel died")
        self.close()
