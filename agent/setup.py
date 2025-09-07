"""
Agent build setup
"""

from setuptools import setup, find_packages
import sys
import os

# Read requirements
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Platform-specific requirements
platform_requirements = []
if sys.platform.startswith('win'):
    platform_requirements.append('pywin32')
elif sys.platform.startswith('linux'):
    platform_requirements.append('python-ptrace')

setup(
    name='c2-agent',
    version='2.0.0',
    description='C2 Framework Agent',
    packages=find_packages(),
    install_requires=requirements + platform_requirements,
    entry_points={
        'console_scripts': [
            'c2-agent=main:main',
        ],
    },
    options={
        'build': {
            'build_base': 'build'
        },
        'py2exe': {
            'bundle_files': 1,
            'compressed': True,
            'optimize': 2,
            'dist_dir': 'dist',
            'excludes': ['tkinter'],
        }
    },
    zipfile=None,
)
