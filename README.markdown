# PyAPNs 

A Python library for interacting with the Apple Push Notification service 
(APNs)

## Installation

Either download the source from GitHub or use easy_install:

    $ easy_install apns

## Sample usage

```python
import time
from apns import APNs, Frame, Payload

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

### Enhanced Message with immediate error-response
```python
apns_enhanced = APNs(use_sandbox=True, cert_file='apns.pem', enhanced=True)
```

Send a notification. note that `identifer` is the information to indicate which message has error in error-response payload.
```python
token_hex = 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b87'
payload = Payload(alert="Hello World!", sound="default", badge=1)
identifier = random.getrandbits(32)
apns_enhanced.gateway_server.send_notification(token_hex, payload, identifier=identifier)
```

Callback when error-response occur, with parameter {'status': 8, 'identifier': 1}.
[Status code reference](https://developer.apple.com/library/ios/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Chapters/CommunicatingWIthAPS.html#//apple_ref/doc/uid/TP40008194-CH101-SW4)
```python
def response_listener(error_response):
    _logger.debug("client get error-response: " + str(error_response))

apns_enhanced.gateway_server.register_response_listener(response_listener)
```

Manually close thread of reading error-response if you want discard future error-responses.
```python
apns_enhanced.gateway_server.close_read_thread()
```

Extra log messages when error-response occur, auto-resent afterwards.

    got error-response from APNS:(8, 1)
    rebuilding connection to APNS
    resending 9 notifications to APNS
    resending notification with id:2 to APNS
    resending notification with id:3 to APNS
    resending notification with id:4 to APNS

Caveats:

* Currently support single notification only

Problem Addressed ([Reference to Redth](http://redth.codes/the-problem-with-apples-push-notification-ser/)):

* Async response of error response and response time varies from 0.1 ~ 0.8 secs by observation
* Sent success do not response, which means client cannot always expect for response.
* Async close write stream connection after error-response.
* All notification sent after failed notification are discarded, the responding error-response and closing client's write connection will be delayed
* Sometimes APNS close socket connection arbitrary

Solution:

* Non-blocking ssl socket connection to send notification without waiting for response.
* A separate thread for constantly checking error-response from read connection.
* A sent notification buffer used for re-sending notification that were sent after failed notification, or arbitrary connection close by apns.
* Reference to [non-blocking apns pull request by minorblend](https://github.com/djacobs/PyAPNs/pull/25), [enhanced message by hagino3000](https://github.com/voyagegroup/apns-proxy-server/blob/065775f87dbf25f6b06f24edc73dc5de4481ad36/apns_proxy_server/worker.py#l164-209)

Result:

* Send notification at throughput of 1000/secs
* In worse case of when 1st notification sent failed, error-response respond after 1 secs and 999 notification sent are discarded by APNS at the mean time, all discarded 999 notifications will be resent without loosing any of them. With the same logic, if notification resent failed, it will resent rest of resent notification after the failed one.

[Test Script](https://gist.github.com/jimhorng/594401f68ce48282ced5)

## Travis Build Status

[![Build Status](https://secure.travis-ci.org/djacobs/PyAPNs.png?branch=master)](http://travis-ci.org/djacobs/PyAPNs)

## Further Info

[iOS Reference Library: Local and Push Notification Programming Guide][a1]

## Credits

Written and maintained by Simon Whitaker at [Goo Software Ltd][goo].

[a1]:http://developer.apple.com/iphone/library/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Introduction/Introduction.html#//apple_ref/doc/uid/TP40008194-CH1-SW1
[goo]:http://www.goosoftware.co.uk/
