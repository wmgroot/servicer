import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "servicer",
    version = "0.3.4",
    author = "Matt Groot",
    author_email = "",
    description = ("CI/CD Automation Framework"),
    license = "BSD3",
    keywords = "ci cd automation environment service",
    url = "https://github.com/wmgroot/servicer",
    packages = find_packages(),
    include_package_data=True,
    long_description = read('README.md'),
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires = [
        'PyYAML==3.12',
        'requests==2.18.4',
    ],
    entry_points = {
        'console_scripts': [
            'servicer = servicer.servicer:main',
        ],
    },
)
