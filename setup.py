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
        "Programming Language :: Python :: 3.8",
    ],
    description="A remote jupyter ipykernel via ssh",
    install_requires=[
        "tornado>=6.1.0,<=6.2.0",
        "jupyter_client>=6.1.12,<6.2.0",
        "jupyterlab>=3.0.0,<3.1.0",
        "wexpect==3.3.2;platform_system=='Windows'",
        "pexpect==4.8.0;platform_system!='Windows'",
    ],
    extras_require={
        "dev": {"twine", "bumpversion", "black", "pylint", "wheel"},
    },
    data_files=[
        (
            "etc/jupyter/jupyter_notebook_config.d",
            ["ssh_ipykernel/ssh_ipykernel_interrupt/etc/ssh-ipykernel-interrupt.json"],
        ),
    ],
    license="MIT license",
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/markdown",
    # packages=find_packages(),
    include_package_data=True,
    keywords="ssh_ipykernel",
    name="ssh_ipykernel",
    packages=find_packages(exclude=["ssh_ipykernel_interrupt"]),
    python_requires=">=3.5",
    url="https://github.com/bernhard-42/ssh_ipykernel",
    version="1.1.0",
    zip_safe=False,
)
