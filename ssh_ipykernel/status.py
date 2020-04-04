import os
import mmap
import hashlib

from ssh_ipykernel.utils import decode_utf8


class Status:
    """Store status of kernel start in mmap'd file for external tools

    Arguments:
        connection_info {dict} -- A ipykernel connection info

    Keyword Arguments:
        status_folder {str} -- Folder where to save the status (default: {"~/.ssh_ipykernel"})
    """

    UNKNOWN = 0
    DOWN = 1
    UNREACHABLE = 2
    KERNEL_KILLED = 3
    STARTING = 4
    RUNNING = 5
    CONNECT_FAILED = 6

    MESSAGES = {
        UNKNOWN: "Unknown",
        DOWN: "Cluster down",
        UNREACHABLE: "Cluster unreachable",
        KERNEL_KILLED: "Kernel killed",
        STARTING: "Starting",
        RUNNING: "Running",
        CONNECT_FAILED: "Connect failed",
    }

    ENDIAN = "little"

    def __init__(self, connection_info, logger, status_folder="~/.ssh_ipykernel"):
        self._logger = logger

        self.status_folder = os.path.expanduser(status_folder)
        filename = "%s.status" % self.create_hash(connection_info)
        self.status_file = os.path.join(self.status_folder, filename)
        self.status_available = True
        self.status = self.create_or_get()

    def create_hash(self, connection_info):
        conn_str = "%d-%d-%d-%d-%d" % (
            connection_info["shell_port"],
            connection_info["iopub_port"],
            connection_info["stdin_port"],
            connection_info["control_port"],
            connection_info["hb_port"],
        )
        h = hashlib.sha256()
        h.update(conn_str.encode())
        return h.hexdigest()

    def create_or_get(self):
        """Create the status file

        Returns:
            [mmap] -- Memory mapped status file
        """
        if not os.path.exists(self.status_folder):
            try:
                os.mkdir(self.status_folder)
            except Exception as ex:
                self._logger.error("Cannot create %s" % self.status_folder)
                self._logger.error(str(ex))
                self.status_available = False

        if self.status_available and not os.path.exists(self.status_file):
            self._logger.debug("Creating new status file %s" % self.status_file)
            try:
                with open(self.status_file, "wb") as fd:
                    fd.write((0).to_bytes(12, Status.ENDIAN))
            except Exception as ex:
                self._logger.error("Cannot initialize %s" % self.status_folder)
                self._logger.error(str(ex))
                self.status_available = False

        if self.status_available:
            self._logger.debug("Attaching to status file %s" % self.status_file)
            fd = open(self.status_file, "r+b")
            return mmap.mmap(fd.fileno(), 0)
        else:
            return None

    def _to_bytes(self, value, length):
        return value.to_bytes(length, Status.ENDIAN, signed=False)

    def _from_bytes(self, value):
        return int.from_bytes(value, Status.ENDIAN, signed=False)

    def _set_status(self, status, pid, sudo):
        """Set status if status file exists

        Arguments:
            status {int} -- Status.<value>
        """
        if self.status_available:
            if pid == None:
                pid = self.get_pid()
            if sudo == None:
                sudo = self.is_sudo()

            new_status = self._to_bytes(status, 2) + self._to_bytes(pid, 8)
            new_status += self._to_bytes(1 if sudo else 0, 2)
            self.status[:12] = new_status
            self.status.flush()
            self._logger.debug(
                "Status for remote pid {pid}: {status}".format(
                    status=Status.MESSAGES[status], pid=pid
                )
            )

    def _get_status(self):
        """Get status if status file exists

        Returns:
            int -- Status.<value>
        """
        if self.status_available:
            return self._from_bytes(self.status[:2])
        else:
            return Status.UNKNOWN

    def get_pid(self):
        """Get remote pid of a running ssh_ipykernel

        Returns:
            int -- pid
        """
        if self.status_available:
            return self._from_bytes(self.status[2:10])
        else:
            return -1

    def is_sudo(self):
        """Get sudo state of a running ssh_ipykernel

        Returns:
            bool -- True if sudo is used, else False
        """
        if self.status_available:
            return self._from_bytes(self.status[10:12]) == 1
        else:
            return False

    def set_unreachable(self, pid=None, sudo=None):
        """Set current status to Status.UNREACHABLE
        """
        self._set_status(Status.UNREACHABLE, pid, sudo)

    def set_kernel_killed(self, pid=None, sudo=None):
        """Set current status to Status.KERNEL_KILLED
        """
        self._set_status(Status.KERNEL_KILLED, pid, sudo)

    def set_starting(self, pid=None, sudo=None):
        """Set current status to Status.STARTING
        """
        self._set_status(Status.STARTING, pid, sudo)

    def set_running(self, pid, sudo):
        """Set current status to Status.RUNNING
        """
        self._set_status(Status.RUNNING, pid, sudo)

    def set_down(self, pid=None, sudo=None):
        """Set current status to Status.DOWN
        """
        self._set_status(Status.DOWN, pid, sudo)

    def set_connect_failed(self, pid=None, sudo=None):
        """Set current status to Status.CONNECT_FAILED
        """
        self._set_status(Status.CONNECT_FAILED, pid, sudo)

    def is_unknown(self):
        """Check for Status.UNKNOWN

        Returns:
            bool -- True if current status is Status.UNKNOWN
        """
        return self._get_status() == Status.UNKNOWN

    def is_unreachable(self):
        """Check for Status.UNREACHABLE

        Returns:
            bool -- True if current status is Status.UNREACHABLE
        """
        return self._get_status() == Status.UNREACHABLE

    def is_kernel_killed(self):
        """Check for Status.KERNEL_KILLED

        Returns:
            bool -- True if current status is Status.KERNEL_KILLED
        """
        return self._get_status() == Status.KERNEL_KILLED

    def is_starting(self):
        """Check for Status.STARTING

        Returns:
            bool -- True if current status is Status.STARTING
        """
        return self._get_status() == Status.STARTING

    def is_running(self):
        """Check for Status.RUNNING

        Returns:
            bool -- True if current status is Status.RUNNING
        """
        return self._get_status() == Status.RUNNING

    def is_down(self):
        """Check for Status.DOWN

        Returns:
            bool -- True if current status is Status.DOWN
        """
        return self._get_status() == Status.DOWN

    def is_connect_failed(self):
        """Check for Status.CONNECT_FAILED

        Returns:
            bool -- True if current status is Status.CONNECT_FAILED
        """
        return self._get_status() == Status.CONNECT_FAILED

    def close(self):
        """Close status file if exists
        """
        try:
            if self.status_available:
                os.remove(self.status_file)
            # else:
            #     self._logger.info("no need to delete status file")
        except Exception as ex:
            self._logger.error(str(ex))

    def get_status_message(self):
        """Get human readable versionof status
        """
        return Status.MESSAGES[self._get_status()]
