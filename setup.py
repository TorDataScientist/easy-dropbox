# -*- coding: utf-8 -*-
from glob import glob
from os.path import basename
from os.path import splitext
from pathlib import Path

from setuptools import setup
from setuptools import find_packages

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

def _requires_from_file(filename):
    return open(filename).read().splitlines()

packages = [
    'ezdbx'
]

setup(
    name='ez-dropbox',
    version='1.0.0',
    license="MIT License",
    description="You can easily operate Dropbox!",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='TorDataScientist',
    url='https://github.com/TorDataScientist/ez-dropbox',
    packages=packages,
    install_requires=_requires_from_file('requirements.txt')
    #entry_points={'console_scripts': console_scripts},
    # other arguments omitted
)