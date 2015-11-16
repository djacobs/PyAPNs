#!/usr/bin/env python
# coding: utf-8
from apns import *
from binascii import a2b_hex
from random import random

import hashlib
import os
import six
import time
import unittest

TEST_CERTIFICATE = "certificate.pem" # replace with path to test certificate

NUM_MOCK_TOKENS = 10
mock_tokens = []
for i in range(0, NUM_MOCK_TOKENS):
    mock_tokens.append(six.b(hashlib.sha256(six.b("%.12f" % random())).hexdigest()))

def mock_chunks_generator():
    BUF_SIZE = 64
    # Create fake data feed
    data = six.binary_type()

    for t in mock_tokens:
        token_bin       = a2b_hex(t)
        token_length    = len(token_bin)

        data += APNs.packed_uint_big_endian(int(time.time()))
        data += APNs.packed_ushort_big_endian(token_length)
        data += token_bin

    while data:
        yield data[0:BUF_SIZE]
        data = data[BUF_SIZE:]


class TestAPNs(unittest.TestCase):
    """Unit tests for PyAPNs"""

    def setUp(self):
        """docstring for setUp"""
        pass

    def tearDown(self):
        """docstring for tearDown"""
        pass

    def testConfigs(self):
        apns_test = APNs(use_sandbox=True)
        apns_prod = APNs(use_sandbox=False)

        self.assertEqual(apns_test.gateway_server.port, 2195)
        self.assertEqual(apns_test.gateway_server.server,
            'gateway.sandbox.push.apple.com')
        self.assertEqual(apns_test.feedback_server.port, 2196)
        self.assertEqual(apns_test.feedback_server.server,
            'feedback.sandbox.push.apple.com')

        self.assertEqual(apns_prod.gateway_server.port, 2195)
        self.assertEqual(apns_prod.gateway_server.server,
            'gateway.push.apple.com')
        self.assertEqual(apns_prod.feedback_server.port, 2196)
        self.assertEqual(apns_prod.feedback_server.server,
            'feedback.push.apple.com')

    def testGatewayServer(self):
        pem_file = TEST_CERTIFICATE
        apns = APNs(use_sandbox=True, cert_file=pem_file, key_file=pem_file)
        gateway_server = apns.gateway_server

        self.assertEqual(gateway_server.cert_file, apns.cert_file)
        self.assertEqual(gateway_server.key_file, apns.key_file)

        token_hex = 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c'
        payload   = Payload(
            alert = "Hello World!",
            sound = "default",
            badge = 4
        )
        notification = gateway_server._get_notification(token_hex, payload)

        expected_length = (
            1                       # leading null byte
            + 2                     # length of token as a packed short
            + len(token_hex) / 2    # length of token as binary string
            + 2                     # length of payload as a packed short
            + len(payload.json())   # length of JSON-formatted payload
        )

        self.assertEqual(len(notification), expected_length)
        self.assertEqual(notification[0], six.b('\0')[0])

    def testFeedbackServer(self):
        pem_file = TEST_CERTIFICATE
        apns = APNs(use_sandbox=True, cert_file=pem_file, key_file=pem_file)
        feedback_server = apns.feedback_server

        self.assertEqual(feedback_server.cert_file, apns.cert_file)
        self.assertEqual(feedback_server.key_file, apns.key_file)

        # Overwrite _chunks() to call a mock chunk generator
        feedback_server._chunks = mock_chunks_generator

        i = 0;
        for (token_hex, fail_time) in feedback_server.items():
            self.assertEqual(token_hex, mock_tokens[i])
            i += 1
        self.assertEqual(i, NUM_MOCK_TOKENS)

    def testPayloadAlert(self):
        pa = PayloadAlert('foo')
        d = pa.dict()
        self.assertEqual(d['body'], 'foo')
        self.assertFalse('action-loc-key' in d)
        self.assertFalse('loc-key' in d)
        self.assertFalse('loc-args' in d)
        self.assertFalse('launch-image' in d)

        pa = PayloadAlert('foo', action_loc_key='bar', loc_key='wibble',
            loc_args=['king','kong'], launch_image='wobble')
        d = pa.dict()
        self.assertEqual(d['body'], 'foo')
        self.assertEqual(d['action-loc-key'], 'bar')
        self.assertEqual(d['loc-key'], 'wibble')
        self.assertEqual(d['loc-args'], ['king','kong'])
        self.assertEqual(d['launch-image'], 'wobble')

        pa = PayloadAlert(loc_key='wibble')
        d = pa.dict()
        self.assertTrue('body' not in d)
        self.assertEqual(d['loc-key'], 'wibble')

    def testPayload(self):
        # Payload with just alert
        p = Payload(alert=PayloadAlert('foo'))
        d = p.dict()
        self.assertTrue('alert' in d['aps'])
        self.assertTrue('sound' not in d['aps'])
        self.assertTrue('badge' not in d['aps'])

        # Payload with just sound
        p = Payload(sound="foo")
        d = p.dict()
        self.assertTrue('sound' in d['aps'])
        self.assertTrue('alert' not in d['aps'])
        self.assertTrue('badge' not in d['aps'])

        # Payload with just badge
        p = Payload(badge=1)
        d = p.dict()
        self.assertTrue('badge' in d['aps'])
        self.assertTrue('alert' not in d['aps'])
        self.assertTrue('sound' not in d['aps'])

        # Payload with just badge removal
        p = Payload(badge=0)
        d = p.dict()
        self.assertTrue('badge' in d['aps'])
        self.assertTrue('alert' not in d['aps'])
        self.assertTrue('sound' not in d['aps'])

        # Test plain string alerts
        alert_str = 'foobar'
        p = Payload(alert=alert_str)
        d = p.dict()
        self.assertEqual(d['aps']['alert'], alert_str)
        self.assertTrue('sound' not in d['aps'])
        self.assertTrue('badge' not in d['aps'])

        # Test custom payload
        alert_str = 'foobar'
        custom_dict = {'foo': 'bar'}
        p = Payload(alert=alert_str, custom=custom_dict)
        d = p.dict()
        self.assertEqual(d, {'foo': 'bar', 'aps': {'alert': 'foobar'}})

    def testFrame(self):
        identifier = 1
        expiry = 3600
        token_hex = 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c'
        payload   = Payload(
            alert = "Hello World!",
            sound = "default",
            badge = 4
        )
        priority = 10

        frame = Frame()
        frame.add_item(token_hex, payload, identifier, expiry, priority)

        f = six.b('\x02\x00\x00\x00t\x01\x00 \xb5\xbb\x9d\x80\x14\xa0\xf9\xb1\xd6\x1e!\xe7\x96\xd7\x8d\xcc\xdf\x13R\xf2<\xd3(\x12\xf4\x85\x0b\x87\x8a\xe4\x94L\x02\x00<{"aps":{"sound":"default","badge":4,"alert":"Hello World!"}}\x03\x00\x04\x00\x00\x00\x01\x04\x00\x04\x00\x00\x0e\x10\x05\x00\x01\n')
        self.assertEqual(f, frame.data())

    def testPayloadTooLargeError(self):
        # The maximum size of the JSON payload is MAX_PAYLOAD_LENGTH
        # bytes. First determine how many bytes this allows us in the
        # raw payload (i.e. before JSON serialisation)
        json_overhead_bytes = len(Payload('.').json()) - 1
        max_raw_payload_bytes = MAX_PAYLOAD_LENGTH - json_overhead_bytes

        # Test ascii characters payload
        Payload('.' * max_raw_payload_bytes)
        self.assertRaises(PayloadTooLargeError, Payload,
            '.' * (max_raw_payload_bytes + 1))

        # Test unicode 2-byte characters payload
        Payload(u'\u0100' * int(max_raw_payload_bytes / 2))
        self.assertRaises(PayloadTooLargeError, Payload,
            u'\u0100' * (int(max_raw_payload_bytes / 2) + 1))

if __name__ == '__main__':
    unittest.main()
