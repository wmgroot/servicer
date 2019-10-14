import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    author = 'Matt Groot',
    author_email = '',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
    ],
    description = ('CI/CD Automation Framework'),
    entry_points = {
        'console_scripts': [
            'servicer = servicer.servicer:main',
        ],
    },
    include_package_data = True,
    install_requires = [
        'ruamel.yaml==0.15.100',
        'requests==2.20.1',
    ],
    keywords = 'ci cd automation environment service',
    license = 'BSD3',
    long_description = read('README.md'),
    long_description_content_type='text/markdown',
    name = 'servicer',
    packages = find_packages(),
    python_requires = '>=3.5',
    url = 'https://github.com/wmgroot/servicer',
    version = '0.11.12',
)
