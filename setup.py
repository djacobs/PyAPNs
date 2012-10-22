from distutils.core import setup

setup(
    author = 'Simon Whitaker',
    author_email = 'simon@goosoftware.co.uk',
    description = 'A python library for interacting with the Apple Push Notification Service',
    download_url = 'http://github.com/simonwhitaker/PyAPNs',
    license = 'unlicense.org',
    name = 'apns',
    py_modules = ['apns'],
    scripts = ['apns-send'],
    url = 'http://www.goosoftware.co.uk/',
    version = '1.1.2',
)
