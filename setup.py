#!/usr/bin/env python
# -*- coding: utf-8 -*-
import setuptools


def get_long_description(path):
    with open(path) as fh:
        return fh.read()


setuptools.setup(
    # Required fields:
    name='squint',
    version='0.0.2',
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
    python_requires='>=2.6.7, !=3.0.*, !=3.1.*',
    long_description=get_long_description('README.rst'),
    long_description_content_type='text/x-rst',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
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
