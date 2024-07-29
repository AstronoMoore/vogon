from setuptools import setup, find_packages
setup_requires=['setuptools_scm'],

setup(
    name='vogon',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
    install_requires=[
        'pandas',
        'astropy',
        'requests',
        'lasair',
    ],
)
