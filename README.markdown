# PyAPNs 

A Python library for interacting with the Apple Push Notification service 
(APNs)

## Installation

Either download the source from GitHub or use easy_install:

    $ easy_install apns

## Sample usage

```python
import time
from apns import APNs, Payload

apns = APNs(use_sandbox=True, cert_file='cert.pem', key_file='key.pem')

# Send a notification
token_hex = 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b87'
payload = Payload(alert="Hello World!", sound="default", badge=1)
apns.gateway_server.send_notification(token_hex, payload)

# Send multiple notifications in a single transmission
frame = Frame()
identifier = 1
expiry = time.time()+3600
priority = 10
frame.add_item('b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b87', payload, identifier, expiry, priority)
apns.gateway_server.send_notification_multiple(frame)

# Get feedback messages
for (token_hex, fail_time) in apns.feedback_server.items():
    # do stuff with token_hex and fail_time
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
