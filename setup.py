#!/usr/bin/env python
"""Setup script for completeness-loop package."""

from setuptools import setup, find_packages

setup(
    name="completeness-loop",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "completeness-loop=src.cli:main",
            "cl-agent=src.cli:main",
        ],
    },
)
