import argparse
import json
import sys
from .kernel import SshKernel


def main(host, connection_info, python_path, sudo, timeout, env):
    """Main function to be called as module to create SshKernel

    Arguments:
        host {str} -- host where the remote ipykernel should be started
        connection_info {dict} -- Local ipykernel connection info as provided by Juypter lab
        python_path {str} -- Remote python path to be used to start ipykernel
        sudo {bool} -- Start ipykernel as root if necessary (default: {False})
        timeout {int} -- SSH connection timeout (default: {5})
        env {str} -- Environment variables passd to the ipykernel "VAR1=VAL1 VAR2=VAL2" (default: {""})
    """
    kernel = SshKernel(host, connection_info, python_path, sudo, timeout, env)
    try:
        kernel.create_remote_connection_info()
        kernel.start_kernel_and_tunnels()
    except:
        kernel._logger.error("Kernel could not be started")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    #    parser._action_groups.pop()
    optional = parser.add_argument_group("optional arguments")
    optional.add_argument(
        "--help",
        "-h",
        action="help",
        default=argparse.SUPPRESS,
        help="show this help message and exit",
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
    optional.add_argument(
        "-s", action="store_true", help="sudo required to start kernel on the remote machine"
    )

    required = parser.add_argument_group("required arguments")
    required.add_argument("--file", "-f", required=True, help="jupyter kernel connection file")
    required.add_argument("--host", "-H", required=True, help="remote host")
    required.add_argument("--python", "-p", required=True, help="remote python_path")
    args = parser.parse_args()

    try:
        with open(args.file, "r") as fd:
            connection_info = json.loads(fd.read())
    except Exception as ex:
        print(ex)
        sys.exit(1)

    sys.exit(main(args.host, connection_info, args.python, args.s, args.timeout, args.env))
