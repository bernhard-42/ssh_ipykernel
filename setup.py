#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

import platform
from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.md") as history_file:
    history = history_file.read()

setup(
    author="Bernhard Walter",
    author_email="b_walter@arcor.de",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="A remote jupyter ipykernel via ssh",
    install_requires=[
        "tornado>=6.0.3,<=6.1.0",
        "jupyter_client>=5.3.1,<5.4.0",
        "jupyterlab>=2.1.0,<2.2.0",
        "wexpect==3.3.2;platform_system=='Windows'",
        "pexpect==4.7.0;platform_system!='Windows'",
    ],
    data_files=[
        (
            "etc/jupyter/jupyter_notebook_config.d",
            ["ssh_ipykernel/ssh_ipykernel_interrupt/etc/ssh-ipykernel-interrupt.json"],
        ),
    ],
    license="MIT license",
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    keywords="ssh_ipykernel",
    name="ssh_ipykernel",
    # packages=find_packages(include=["ssh_ipykernel", "interrupt_ssh_ipykernel"]),
    python_requires=">=3.5",
    url="https://github.com/bernhard-42/ssh_ipykernel",
    version="1.0.3",
    zip_safe=False,
)
