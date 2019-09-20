import os
import mmap

class Status:
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
        if self.status_available:
            self.status[0] = status
            self.status.flush()

    def set_unreachable(self):
        self._set_status(Status.UNREACHABLE)

    def set_kernel_killed(self):
        self._set_status(Status.KERNEL_KILLED)

    def set_starting(self):
        self._set_status(Status.STARTING)

    def set_running(self):
        self._set_status(Status.RUNNING)

    def set_down(self):
        self._set_status(Status.DOWN)

    def set_connect_failed(self):
        self._set_status(Status.CONNECT_FAILED)
        
    def _get_status(self):
        if self.status_available:
            return self.status[0]
        else:
            return Status.UNKNOWN

    def is_unknown(self):
        return self._get_status() == Status.UNKNOWN

    def is_unreachable(self):
        return self._get_status() == Status.UNREACHABLE

    def is_kernel_killed(self):
        return self._get_status() == Status.KERNEL_KILLED

    def is_starting(self):
        return self._get_status() == Status.STARTING

    def is_running(self):
        return self._get_status() == Status.RUNNING

    def is_down(self):
        return self._get_status() == Status.DOWN

    def is_connect_failed(self):
        return self._get_status() == Status.CONNECT_FAILED
        
    def close(self):
        try:
            if self.status_available:
                os.remove(self.status_file)
            else:
                print("no need to delete status file")
        except Exception as ex:
            print(ex)

    def get_status_message(self):
        return Status.MESSAGES[self._get_status()]
