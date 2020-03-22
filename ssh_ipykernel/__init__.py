# -*- coding: utf-8 -*-

"""Top-level package for SSH Kernel."""

from notebook.utils import url_path_join

__author__ = """Bernhard Walter"""
__email__ = "b_walter@arcor.de"
from ._version import __version__, __version_info__

from .ssh_ipykernel_interrupt import SshInterruptHandler


def load_jupyter_server_extension(nb_server_app):
    """
    Called when the extension is loaded.

    Args:
        nb_server_app (NotebookWebApplication): handle to the Notebook webserver instance.
    """
    web_app = nb_server_app.web_app
    SshInterruptHandler.nbapp = nb_server_app
    host_pattern = ".*$"
    route_pattern = url_path_join(web_app.settings["base_url"], "/interrupt")
    web_app.add_handlers(host_pattern, [(route_pattern, SshInterruptHandler)])
