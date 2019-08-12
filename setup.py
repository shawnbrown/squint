import setuptools


#with open('README.rst') as fh:
#    long_description = fh.read()


setuptools.setup(
    name='squint',
    version='0.0.1',
    author='Shawn Brown',
    author_email='shawnbrown@users.noreply.github.com',
    description='Simple query interface for tabular data.',
    #long_description=long_description,
    #long_description_content_type='text/x-rst',
    url='https://github.com/shawnbrown/squint',
    packages=setuptools.find_packages(exclude=['docs', 'tests']),
    classifiers=[
        'Development Status :: 4 - Beta',
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
    license='Apache 2.0',
    python_requires='>=2.6.7, !=3.0.*, !=3.1.*',
    install_requires=[],  # <- TODO: Break-out "get_reader" and add here.
)
