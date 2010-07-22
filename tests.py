from pyapns import APNs
from random import random

import hashlib
import os
import time
import unittest

TEST_CERTIFICATE = "certificate.pem" # replace with path to test certificate

NUM_MOCK_TOKENS = 10
mock_tokens = []
for i in range(0, NUM_MOCK_TOKENS):
    mock_tokens.append(hashlib.sha256("%.12f" % random()).hexdigest())

def mock_chunks_generator():
    BUF_SIZE = 64
    # Create fake data feed
    data = ''
    
    for t in mock_tokens:
        token_bin       = APNs.byte_string_from_hex(t)
        token_length    = len(token_bin)
        
        data += APNs.packed_uint_big_endian(int(time.time()))
        data += APNs.packed_ushort_big_endian(token_length)
        data += token_bin
        
    while data:
        yield data[0:BUF_SIZE]
        data = data[BUF_SIZE:]


class TestDataset(unittest.TestCase):
    """Unit tests for the Dataset class"""

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
        self.assertEqual(apns_test.gateway_server.server, 'gateway.sandbox.push.apple.com')
        self.assertEqual(apns_test.feedback_server.port, 2196)
        self.assertEqual(apns_test.feedback_server.server, 'feedback.sandbox.push.apple.com')

        self.assertEqual(apns_prod.gateway_server.port, 2195)
        self.assertEqual(apns_prod.gateway_server.server, 'gateway.push.apple.com')
        self.assertEqual(apns_prod.feedback_server.port, 2196)
        self.assertEqual(apns_prod.feedback_server.server, 'feedback.push.apple.com')
        
    def testGatewayServer(self):
        pem_file        = TEST_CERTIFICATE
        apns            = APNs(use_sandbox=True, cert_file=pem_file, key_file=pem_file)
        gateway_server  = apns.gateway_server

        self.assertEqual(gateway_server.cert_file, apns.cert_file)
        self.assertEqual(gateway_server.key_file, apns.key_file)

    def testFeedbackServer(self):
        pem_file        = TEST_CERTIFICATE
        apns            = APNs(use_sandbox=True, cert_file=pem_file, key_file=pem_file)
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

if __name__ == '__main__':
    unittest.main()
