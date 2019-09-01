import argparse
import json
import logging
import os
import signal
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
fname = os.path.expanduser("~/{fname}")
from jupyter_client import write_connection_file
write_connection_file(fname=fname, ip="{ip}", key=b"{key}", transport="{transport}", signature_scheme="{signature_scheme}", kernel_name="{kernel_name}")
fd = open(fname, "r")
ci = json.loads(fd.read())
fd.close()
ports = json.dumps({{k:v for k,v in ci.items() if "_port" in k}})
print(ports)
"""


class SshKernel:

    def __init__(self, host, connection_info, python_path, sudo, timeout, env):
        self.host = host
        self.connection_info = connection_info
        self.python_path = python_path
        self.sudo = sudo
        self.timeout = timeout
        self.env = env

        self._connection = None

        self.remote_ports = {}
        self.uuid = str(uuid.uuid4())
        self.fname = ".ssh_ipykernel_%s.json" % self.uuid

        self._setup_logging()
        self._logger.debug("Remote kernel info file ~/{0}".format(self.fname))

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
            self._connection.sendintr() # send SIGINT

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

    def connect(self, ssh_config="~/.ssh/config", retries=5):
        delays = [2, 4, 8, 16][:retries - 1]
        for delay in delays:
            try:
                connection = pxssh.pxssh(timeout=self.timeout)
                connection.login(self.host, ssh_config=os.path.expanduser(ssh_config))
                self._connection = connection
                self._logger.info("Connected to host '%s'" % self.host)
                break
            except Exception as e:
                print("failed to login with ssh")
                if e == "connection closed":
                    self._logger.warning("Unexpected connection close, waiting for %ds" % delay)
                    time.sleep(delay)
                else:
                    self._logger.info(e)
                    break
        if self._connection is None:
            raise SshKernelException("Connection failed")

    def close(self):
        if self._connection is not None and self._connection.isalive():
            self._connection.logout()

    def _cmd(self, cmd):
        self._connection.sendline(cmd)
        self._connection.prompt()
        result = self._connection.before
        return self._decode_utf8(result).split("\r\n")[1:]

    def execute(self, cmd):
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

    def start(self):
        python_full_path = os.path.join(self.python_path, "bin/python")
        self.connect()
        result = self.execute("uptime")
        if result[0] != 0:
            raise SshKernelException("Could not execute command")

        # Create a remote kernel_info file
        script = KERNEL_SCRIPT.format(fname=self.fname, **self.connection_info)
        result = self.execute("{python} -c '{command}'".format(
            python=python_full_path, command="; ".join(script.strip().split("\n"))))
        if result[0] == 0:
            self.remote_ports = json.loads(result[1][0])
            self._logger.debug("Remote ports = %s" % self.remote_ports)
        else:
            raise SshKernelException("Could not create kernel_info file")

        # start remote kernel with remote kernel_info file
        self._logger.info("Starting remote kernel ...")
        sudo = "sudo " if self.sudo else ""
        env =  "" if self.env is None else " ".join(self.env) + " "
        cmd = "{sudo}{env}{python} -m ipykernel_launcher -f {fname}".format(
            env=env, sudo=sudo, python=python_full_path, fname=self.fname)
        self._logger.debug(cmd)
        # don't use execute, this call will block itself.
        self._connection.sendline(cmd)
        self._logger.info("Remote kernel started")

        # TODO clean up kernel info file
        # self._connection.sendline("rm ~/{fname}".format(fname=self.fname))
        # self._connection.sendline("exit")
        # self._connection.expect("exit")

    def setup_tunnel(self):
        cmd = "ssh -N -o StrictHostKeyChecking=no "
        for port_name in self.remote_ports.keys():
            cmd += "-L 127.0.0.1:{local_port}:127.0.0.1:{remote_port} ".format(
                local_port=self.connection_info[port_name], remote_port=self.remote_ports[port_name])
        cmd += self.host
        self._logger.info("Starting tunnel ...")
        self._logger.debug(cmd)
        self.tunnel = pexpect.spawn(cmd)
        self._logger.info("Tunnel started")

    def check_tunnel(self):
        if not self.tunnel.isalive():
            self._logger.warning("Restarting ssh tunnel!")
            self.setup_tunnel()

    def keep_alive(self):
        while True:
            time.sleep(self.timeout)
            if not self._connection.isalive():
                self._logger.error("Kernel died.")
                for line in self._connection.readlines():
                    if line.strip():
                        self._logger.error(line)
                break

            self.check_tunnel()
