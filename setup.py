from setuptools import setup, find_packages
setup_requires=['setuptools_scm'],

setup(
    name='vogon',
    version='0.1.0',
    author='Thomas Moore',
    author_email='tom.moore017@gmail.com',
    description='A basic data aggregator for astrophysical transients',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=[
        'pandas',
        'astropy',
        'requests',
        'lasair',
    ],
)
