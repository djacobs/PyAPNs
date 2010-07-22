# PyAPNs 

A Python library for interacting with the Apple Push Notification service (APNs)

## Sample usage

    from pyapns import APNs

    apns = APNs(use_sandbox=True, cert_file='cert-file.pem', key_file='key-file.pem')

    # Send some notifications
    token_hex = 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c'
    payload   = {'aps': {alert': {'body': 'Hello world!'}}}
    
    apns.gateway_server.send_notification(token_hex, payload)
    
    # Get feedback messages
    for (token_hex, fail_time) in apns.feedback_server.items():
        # do stuff with token_hex and fail_time

## TODO

1. An APNsPayload class would be nice :)

## Credits

Written and maintained by Simon Whitaker at [Goo Software Ltd](http://www.goosoftware.co.uk/) 

