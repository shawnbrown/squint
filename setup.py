#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ast
import setuptools


def get_long_description(path):
    with open(path) as fh:
        return fh.read()


def get_version(path):
    """Return value of file's __version__ attribute."""
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith('__version__'):
                return ast.parse(line).body[0].value.s
    raise Exception('Unable to find __version__ attribute.')


setuptools.setup(
    # Required fields:
    name='squint',
    version=get_version('squint/__init__.py'),
    description='Simple query interface for tabular data.',
    packages=setuptools.find_packages(exclude=['docs', 'tests']),

    # Recommended fields:
    url='https://github.com/shawnbrown/squint',
    author='Shawn Brown',
    author_email='shawnbrown@users.noreply.github.com',

    # Other fields:
    install_requires=[
        'get-reader[excel,dbf]',
    ],
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    long_description=get_long_description('README.rst'),
    long_description_content_type='text/x-rst',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Utilities',
    ],
)
