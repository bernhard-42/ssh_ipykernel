#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.md') as history_file:
    history = history_file.read()

setup(
    author="Bernhard Walter",
    author_email='b_walter@arcor.de',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="A remote jupyter ipykernel via ssh",
    install_requires=[
        "pexpect==4.7.0",
        "tornado>=6.0.3",
        "jupyter_client>=5.3.1,<5.4.0"
    ],
    license="MIT license",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords='ssh_ipykernel',
    name='ssh_ipykernel',
    packages=find_packages(include=['ssh_ipykernel']),
    python_requires='>=3.6',
    url='https://github.com/bernhard-42/ssh_ipykernel',
    version='0.9.3',
    zip_safe=False
)
