# SSH Kernel - an ipykernel over ssh

A remote jupyterkernel via ssh

* Free software: MIT license

The ideas are heavily based on [remote_ikernel](https://bitbucket.org/tdaff/remote_ikernel), however `ssh_ipykernel`adds some important features

* `jupyter_client`'s function `write_connection_file` is used on the remote server to get free ports
* Local ports (obtained by jupyter also via `write_connection_file`) will be ssh forwarded to the remote ports
* The ssh connection and the tunnel command will be retried in case of network or similar errors
* introduced signal handling with python's `signal` module

## Installation

```bash

pip install ssh_ipykernel
jupyter labextension install interrupt-ipykernel-extension
```

## Usage

* Usage of ssh_ipykernel

  ```text
  $ python -m ssh_ipykernel -h
  usage: __main__.py [--help] [--timeout TIMEOUT] [--env [ENV [ENV ...]]] [-s]
                    --file FILE --host HOST --python PYTHON

  optional arguments:
    --help, -h            show this help message and exit
    --timeout TIMEOUT, -t TIMEOUT
                          timeout for remote commands
    --env [ENV [ENV ...]], -e [ENV [ENV ...]]
                          environment variables for the remote kernel in the
                          form: VAR1=value1 VAR2=value2
    -s                    sudo required to start kernel on the remote machine

  required arguments:
    --file FILE, -f FILE  jupyter kernel connection file
    --host HOST, -H HOST  remote host
    --python PYTHON, -p PYTHON
                          remote python_path
  ```

* Creation of kernel specification

  * from python

    ```python
    import ssh_ipykernel.manage
    ssh_ipykernel.manage.add_kernel(
        host="btest",
        display_name="SSH btest:demo(abc)",
        local_python_path="/opt/miniconda/envs/test36/bin/python",
        remote_python_path="/opt/anaconda/envs/python36",
        sudo=False,
        env="VAR1=demo VAR2=abc",
        timeout=10
    )
    ```

  * from terminal

    ```bash
    python -m ssh_ipykernel.manage --display-name "SSH btest:demo(abc) \
                                   --host btest \
                                   --python /opt/anaconda/envs/python36 \
                                   --env "VAR1=demo VAR2=abc"
    ```

    ```bash
    $ python -m ssh_ipykernel.manage --help

    usage: manage.py [--help] [--display-name DISPLAY_NAME] [--sudo]
                    [--timeout TIMEOUT] [--env [ENV [ENV ...]]] --host HOST
                    --python PYTHON

    optional arguments:
      --help, -h            show this help message and exit
      --display-name DISPLAY_NAME, -d DISPLAY_NAME
                            kernel display name (default is host name)
      --sudo, -s            sudo required to start kernel on the remote machine
      --timeout TIMEOUT, -t TIMEOUT
                            timeout for remote commands
      --env [ENV [ENV ...]], -e [ENV [ENV ...]]
                            environment variables for the remote kernel in the
                            form: VAR1=value1 VAR2=value2

    required arguments:
      --host HOST, -H HOST  remote host
      --python PYTHON, -p PYTHON
                            remote python_path
    ```

* Checking of kernel specification

  ```bash
  $ jupyter-kernelspec list
  Available kernels:
    ssh__ssh_btest_demo_abc_         /Users/bernhard/Library/Jupyter/kernels/ssh__ssh_btest_demo_abc_
  ```

  ```bash
  $ cat /Users/bernhard/Library/Jupyter/kernels/ssh__ssh_btest_demo_abc_/kernel.json
  {
    "argv": [
      "/opt/miniconda/envs/test36/bin/python",
      "-m",
      "ssh_ipykernel",
      "--host",
      "btest",
      "--python",
      "/opt/anaconda/envs/python36",
      "--timeout",
      "10",
      "--env",
      "VAR1=demo VAR2=abc",
      "-f",
      "{connection_file}"
    ],
    "display_name": "SSH btest:demo(abc)",
    "language": "python"
  }
  ```

* Add an ssh config entry to `~/.ssh/config`for the remote host:

  ```text
  Host btest
      HostName btest.example.com
      User john
      Port 22
      IdentityFile ~/.ssh/id_rsa
      ServerAliveInterval 30
      ConnectTimeout 5
      ServerAliveCountMax 5760 
  ```

## Credits

The ideas are heavily based on

* [remote_ikernel](https://bitbucket.org/tdaff/remote_ikernel)
