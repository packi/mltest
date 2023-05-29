from setuptools import setup

setup(
    name='mltest',
    version='0.1.0',
    py_modules=['mltest'],
    install_requires=[
        'Click',
    ],
    entry_points={
        'console_scripts': [
            'mltest = mltest:cli',
        ],
    },
)