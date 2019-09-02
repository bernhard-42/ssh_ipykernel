import getpass
import json
import os
import re
import tempfile
from jupyter_client import kernelspec as ks

PREFIX = "ssh_"

def add_kernel(host, display_name, local_python_path, remote_python_path, env=None, sudo=False, system=False,
               timeout=5):

    def simplify(name):
        return re.sub(r"[^a-zA-Z0-9\-\.\_]", "", name)

    if system:
        username = False
    else:
        username = getpass.getuser()

    kernel_json = {
        "argv": [
            local_python_path, "-m", "ssh_ipykernel", "--host", host, "--python", remote_python_path, "--timeout",
            str(timeout), "-f", "{connection_file}"
        ],
        "display_name": display_name,
        "language": "python"
    }
    if env is not None:
        kernel_json["argv"].insert(-2, "--env")
        kernel_json["argv"].insert(-2, env)

    if sudo:
        kernel_json["argv"].insert(-2, "-s")

    kernel_name = "{prefix}_{display_name}".format(prefix=PREFIX, host=host, display_name=simplify(display_name))
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chmod(temp_dir, 0o755)

        with open(os.path.join(temp_dir, 'kernel.json'), 'w') as fd:
            json.dump(kernel_json, fd, sort_keys=True, indent=2)

        ks.install_kernel_spec(temp_dir, kernel_name, user=username, replace=True)

    return kernel_name
