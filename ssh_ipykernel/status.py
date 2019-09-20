import os
import mmap
import hashlib

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
        CONNECT_FAILED: "Connect failed"
    }

    def __init__(self, connection_info, status_folder="~/.ssh_ipykernel"):
        self.status_folder = os.path.expanduser(status_folder)
        filename = "%s.status" % self.create_hash(connection_info)
        self.status_file = os.path.join(self.status_folder, filename)
        self.status_available = True

        self.status = self.create_or_get()

    def create_hash(self, connection_info):
        conn_str = "%d-%d-%d-%d-%d-%s.status" % (connection_info["shell_port"], connection_info["iopub_port"],
                                                 connection_info["stdin_port"], connection_info["control_port"],
                                                 connection_info["hb_port"], connection_info.get("key", ""))
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
                print("Cannot create %s" % self.status_folder)
                print(ex)
                self.status_available = False

        if self.status_available and not os.path.exists(self.status_file):
            try:
                with open(self.status_file, "wb") as fd:
                    fd.write(bytes([Status.UNKNOWN]))
            except Exception as ex:
                print("Cannot initialize %s" % self.status_folder)
                print(ex)
                self.status_available = False

        if self.status_available:
            fd = open(self.status_file, "r+b")
            return mmap.mmap(fd.fileno(), 0)
        else:
            return None

    def _set_status(self, status):
        """Set status if status file exists

        Arguments:
            status {int} -- Status.<value>
        """
        if self.status_available:
            self.status[0] = status
            self.status.flush()

    def set_unreachable(self):
        """Set current status to Status.UNREACHABLE
        """
        self._set_status(Status.UNREACHABLE)

    def set_kernel_killed(self):
        """Set current status to Status.KERNEL_KILLED
        """
        self._set_status(Status.KERNEL_KILLED)

    def set_starting(self):
        """Set current status to Status.STARTING
        """
        self._set_status(Status.STARTING)

    def set_running(self):
        """Set current status to Status.RUNNING
        """
        self._set_status(Status.RUNNING)

    def set_down(self):
        """Set current status to Status.DOWN
        """
        self._set_status(Status.DOWN)

    def set_connect_failed(self):
        """Set current status to Status.CONNECT_FAILED
        """
        self._set_status(Status.CONNECT_FAILED)

    def _get_status(self):
        """Get status if status file exists

        Returns:
            int -- Status.<value>
        """
        if self.status_available:
            return self.status[0]
        else:
            return Status.UNKNOWN

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
            else:
                print("no need to delete status file")
        except Exception as ex:
            print(ex)

    def get_status_message(self):
        """Get human readable versionof status
        """
        return Status.MESSAGES[self._get_status()]
