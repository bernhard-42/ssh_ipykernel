import argparse
import getpass
import json
import os
import re
import sys
import tempfile
from jupyter_client import kernelspec as ks

PREFIX = "ssh_"


def add_kernel(
    host,
    display_name,
    local_python_path,
    remote_python_path,
    env=None,
    sudo=False,
    system=False,
    timeout=5,
    module="ssh_ipykernel",
    opt_args=None,
):
    """Add a new kernel specification for an SSH Kernel

    Arguments:
        host {str} -- host where the remote ipykernel should be started
        display_name {str} -- Display name for the new kernel
        local_python_path {[type]} -- Local python path to be used (without bin/python)
        remote_python_path {[type]} -- Remote python path to be used (without bin/python)

    Keyword Arguments:
        env {str} -- Environment variables passd to the ipykernel "VAR1=VAL1 VAR2=VAL2" (default: {""})
        sudo {bool} -- Start ipykernel as root if necessary (default: {False})
        system {bool} -- Create kernelspec as user (False) or system (True) (default: {False})
        timeout {int} -- SSH connection timeout (default: {5})

    Returns:
        [type] -- [description]
    """

    def simplify(name):
        return re.sub(r"[^a-zA-Z0-9\-\.\_]", "", name)

    if system:
        username = False
    else:
        username = getpass.getuser()

    if opt_args is None:
        opt_args = []

    kernel_json = {
        "argv": [
            local_python_path,
            "-m",
            module,
            "--host",
            host,
            "--python",
            remote_python_path,
            "--timeout",
            str(timeout),
        ]
        + opt_args
        + ["-f", "{connection_file}",],
        "display_name": display_name,
        "language": "python",
    }
    if env is not None:
        kernel_json["argv"].insert(-2, "--env")
        kernel_json["argv"].insert(-2, env)

    if sudo:
        kernel_json["argv"].insert(-2, "-s")

    kernel_name = "{prefix}_{display_name}".format(
        prefix=PREFIX, host=host, display_name=simplify(display_name)
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chmod(temp_dir, 0o755)

        with open(os.path.join(temp_dir, "kernel.json"), "w") as fd:
            json.dump(kernel_json, fd, sort_keys=True, indent=2)

        ks.install_kernel_spec(temp_dir, kernel_name, user=username, replace=True)

    return kernel_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    optional = parser.add_argument_group("optional arguments")
    optional.add_argument(
        "--help",
        "-h",
        action="help",
        default=argparse.SUPPRESS,
        help="show this help message and exit",
    )
    optional.add_argument(
        "--display-name", "-d", type=str, help="kernel display name (default is host name)"
    )
    optional.add_argument(
        "--sudo",
        "-s",
        action="store_true",
        help="sudo required to start kernel on the remote machine",
    )
    optional.add_argument(
        "--timeout", "-t", type=int, help="timeout for remote commands", default=5
    )
    optional.add_argument(
        "--env",
        "-e",
        nargs="*",
        help="environment variables for the remote kernel in the form: VAR1=value1 VAR2=value2",
    )

    required = parser.add_argument_group("required arguments")
    required.add_argument("--host", "-H", required=True, help="remote host")
    required.add_argument("--python", "-p", required=True, help="remote python_path")
    args = parser.parse_args()

    if args.env:
        env = " ".join(args.env)

    add_kernel(
        host=args.host,
        display_name=args.host if args.display_name is None else args.display_name,
        local_python_path=sys.executable,
        remote_python_path=args.python,
        sudo=args.sudo,
        env=env,
        timeout=args.timeout,
    )
