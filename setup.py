from setuptools import setup, find_packages

setup(
    name="dmpy",
    version="0.22.0",
    description="Python API wrapper for DMP",
    author="IDEA-FAST",
    packages=find_packages(),
    install_requires=[
        "requests",
        "colorama",
        "rarfile",
        "py7zr",
        "pandas",
    ],
    entry_points={
        'console_scripts': [
            'dmpy=dmpy.cli:main',
        ],
    },
    python_requires='>=3.6',
) 
