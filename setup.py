from setuptools import setup

setup(
    name='apns',
    version='3.0.0-alpha.1',
    author='David Jacobs',
    author_email='david@29.io',
    description='A python library for interacting with the Apple Push Notification Service',
    url='http://29.io/',
    download_url='https://github.com/djacobs/PyAPNs',
    license='unlicense.org',
    py_modules=['apns'],
    scripts=['apns-send'],
    install_requires=[
        'PyJWT>=2.0.0',
        # TODO: Add an HTTP/2 client library here (e.g., 'httpx>=0.20.0') once selected for APNS HTTP/2 migration
    ],
)
