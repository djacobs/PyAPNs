# PyAPNs 

A Python library for interacting with the Apple Push Notification service 
(APNs) including enhanced notification format with non-blocking SSL connection.

The original version of PyAPNs is written and maintained by Simon Whitaker (https://github.com/simonwhitaker/PyAPNs), which can be installed using easy_install

	$ easy_install apns
	
Enhanced notification format support using non-blocking SSL connection is added and maintained by Josh Ha-Nyung Chung

## Installation

Download the source from GitHub:

    $ git clone git://github.com/minorblend/PyAPNs.git
    $ cd PyAPNs
    $ sudo python setup.py

## Sample usage

### normal format

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

### enhanced format

```python
from apns import APNs, Payload

apns = APNs(use_sandbox=True, cert_file='cert.pem', key_file='key.pem', enhanced=True)

# Send a notification
token_hex = 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b87'
payload = Payload(alert="Hello World!", sound="default", badge=1)
response = apns.gateway_server.send_notification(token_hex, payload)
if response:
    (status, identifier) = response
    # do something to handle error
    # response DOES NOT correspond to the notification message which is just to be sent. 
    # corresponding notification message can be matched by returned identifier
    # APN connection is closed when APNs returns an error response. PyAPNs does not try to reconnect.

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

## Further Info

[iOS Reference Library: Local and Push Notification Programming Guide][a1]

## Credits

Originally written and maintained by Simon Whitaker at [Goo Software Ltd][goo].

Enhanced format support is added and maintained by Josh Ha-Nyung Chung at [Sunnyloft][sunnyloft].

[a1]:http://developer.apple.com/iphone/library/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Introduction/Introduction.html#//apple_ref/doc/uid/TP40008194-CH1-SW1
[goo]:http://www.goosoftware.co.uk/
[sunnyloft]:http://sunnyloft.com/
