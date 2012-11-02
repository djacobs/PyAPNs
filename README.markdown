# PyAPNs 

A Python library for interacting with the Apple Push Notification service 
(APNs)

## Installation

Either download the source from GitHub or use easy_install:

    $ easy_install apns

## Sample usage

```python
from apns import APNs, Payload

apns = APNs(use_sandbox=True, cert_file='cert.pem', key_file='key.pem')

# Send a notification
token_hex = 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b87'
payload = Payload(alert="Hello World!", sound="default", badge=1)
apns.gateway_server.send_notification(token_hex, payload)

# Get feedback messages
for (token_hex, fail_time) in apns.feedback_server.items():
    # do stuff with token_hex and fail_time
```

## Send a notification in enhanced format
```python
from apns import APNs, Payload, APNResponseError
from datetime import datetime, timedelta

apns = APNs(use_sandbox=True, cert_file='cert.pem', key_file='key.pem', enhanced=True)

token_hex = 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b87'
payload = Payload(alert="Hello World!", sound="default", badge=1)
identifier = 1234
expiry = datetime.utcnow() + timedelta(30) # undelivered notification expires after 30 seconds

try:
    apns.gateway_server.send_notification(token_hex, payload)
except APNResponseError, err:
    # handle apn's error response
    # just tried notification is not sent and this response doesn't belong to that notification.
    # formerly sent notifications should to be looked up with err.identifier to find one which caused this error.
    # when error response is received, connection to APN server is closed.
```

For more complicated alerts including custom buttons etc, use the PayloadAlert 
class. Example:

```python
alert = PayloadAlert("Hello world!", action_loc_key="Click me")
payload = Payload(alert=alert, sound="default")
```

To send custom payload arguments, pass a dictionary to the custom kwarg
of the Payload constructor.

```python
payload = Payload(alert="Hello World!", custom={'sekrit_number':123})
```

## Travis Build Status

[![Build Status](https://secure.travis-ci.org/simonwhitaker/PyAPNs.png?branch=master)](http://travis-ci.org/simonwhitaker/PyAPNs)

## Further Info

[iOS Reference Library: Local and Push Notification Programming Guide][a1]

## Credits

Written and maintained by Simon Whitaker at [Goo Software Ltd][goo].

[a1]:http://developer.apple.com/iphone/library/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Introduction/Introduction.html#//apple_ref/doc/uid/TP40008194-CH1-SW1
[goo]:http://www.goosoftware.co.uk/
