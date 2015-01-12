from distutils.core import setup

setup(
    author = 'David Jacobs',
    author_email = 'david@29.io',
    description = 'A python library for interacting with the Apple Push Notification Service',
    download_url = 'https://github.com/djacobs/PyAPNs',
    license = 'unlicense.org',
    name = 'apns',
    py_modules = ['apns'],
    scripts = ['apns-send'],
    url = 'http://29.io/',
    version = '2.0.1',
)
