# PyAPNs was developed by Simon Whitaker <simon@goosoftware.co.uk>
# Source available at https://github.com/simonwhitaker/PyAPNs
#
# PyAPNs is distributed under the terms of the MIT license.
#
# Copyright (c) 2011 Goo Software Ltd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from binascii import a2b_hex, b2a_hex
from datetime import datetime, timedelta
from time import mktime
from random import getrandbits
from socket import socket, AF_INET, SOCK_STREAM
from struct import pack, unpack

try:
    from ssl import wrap_socket
except ImportError:
    from socket import ssl as wrap_socket

try:
    import json
except ImportError:
    import simplejson as json

MAX_PAYLOAD_LENGTH = 256

class APNs(object):
    """A class representing an Apple Push Notification service connection"""

    def __init__(self, use_sandbox=False, cert_file=None, key_file=None):
        """
        Set use_sandbox to True to use the sandbox (test) APNs servers.
        Default is False.
        """
        super(APNs, self).__init__()
        self.use_sandbox = use_sandbox
        self.cert_file = cert_file
        self.key_file = key_file
        self._feedback_connection = None
        self._gateway_connection = None

    @staticmethod
    def packed_ushort_big_endian(num):
        """
        Returns an unsigned short in packed big-endian (network) form
        """
        return pack('>H', num)

    @staticmethod
    def unpacked_ushort_big_endian(bytes):
        """
        Returns an unsigned short from a packed big-endian (network) byte
        array
        """
        return unpack('>H', bytes)[0]

    @staticmethod
    def packed_uint_big_endian(num):
        """
        Returns an unsigned int in packed big-endian (network) form
        """
        return pack('>I', num)

    @staticmethod
    def unpacked_uint_big_endian(bytes):
        """
        Returns an unsigned int from a packed big-endian (network) byte array
        """
        return unpack('>I', bytes)[0]

    @property
    def feedback_server(self):
        if not self._feedback_connection:
            self._feedback_connection = FeedbackConnection(
                use_sandbox = self.use_sandbox,
                cert_file = self.cert_file,
                key_file = self.key_file
            )
        return self._feedback_connection

    @property
    def gateway_server(self):
        if not self._gateway_connection:
            self._gateway_connection = GatewayConnection(
                use_sandbox = self.use_sandbox,
                cert_file = self.cert_file,
                key_file = self.key_file
            )
        return self._gateway_connection


class APNsConnection(object):
    """
    A generic connection class for communicating with the APNs
    """
    def __init__(self, cert_file=None, key_file=None):
        super(APNsConnection, self).__init__()
        self.cert_file = cert_file
        self.key_file = key_file
        self._socket = None
        self._ssl = None

    def __del__(self):
        self._disconnect();

    def _connect(self):
        # Establish an SSL connection
        self._socket = socket(AF_INET, SOCK_STREAM)
        self._socket.connect((self.server, self.port))
        self._ssl = wrap_socket(self._socket, self.key_file, self.cert_file)

    def _disconnect(self):
        if self._socket:
            self._socket.close()

    def _connection(self):
        if not self._ssl:
            self._connect()
        return self._ssl

    def read(self, n=None):
        return self._connection().read(n)

    def write(self, string):
        return self._connection().write(string)


class PayloadAlert(object):
    def __init__(self, body=None, action_loc_key=None, loc_key=None,
                 loc_args=None, launch_image=None):
        super(PayloadAlert, self).__init__()
        self.body = body
        self.action_loc_key = action_loc_key
        self.loc_key = loc_key
        self.loc_args = loc_args
        self.launch_image = launch_image

    def dict(self):
        d = {}
        if self.body:
            d['body'] = self.body
        if self.action_loc_key:
            d['action-loc-key'] = self.action_loc_key
        if self.loc_key:
            d['loc-key'] = self.loc_key
        if self.loc_args:
            d['loc-args'] = self.loc_args
        if self.launch_image:
            d['launch-image'] = self.launch_image
        return d

class PayloadTooLargeError(Exception):
    def __init__(self):
        super(PayloadTooLargeError, self).__init__()

class Payload(object):
    """A class representing an APNs message payload"""
    def __init__(self, alert=None, badge=None, sound=None, custom={}):
        super(Payload, self).__init__()
        self.alert = alert
        self.badge = badge
        self.sound = sound
        self.custom = custom
        self._check_size()

    def dict(self):
        """Returns the payload as a regular Python dictionary"""
        d = {}
        if self.alert:
            # Alert can be either a string or a PayloadAlert
            # object
            if isinstance(self.alert, PayloadAlert):
                d['alert'] = self.alert.dict()
            else:
                d['alert'] = self.alert
        if self.sound:
            d['sound'] = self.sound
        if self.badge is not None:
            d['badge'] = int(self.badge)

        d = { 'aps': d }
        d.update(self.custom)
        return d

    def json(self):
        return json.dumps(self.dict(), separators=(',',':'), ensure_ascii=False).encode('utf-8')

    def _check_size(self):
        if len(self.json()) > MAX_PAYLOAD_LENGTH:
            raise PayloadTooLargeError()

    def __repr__(self):
        attrs = ("alert", "badge", "sound", "custom")
        args = ", ".join(["%s=%r" % (n, getattr(self, n)) for n in attrs])
        return "%s(%s)" % (self.__class__.__name__, args)


class FeedbackConnection(APNsConnection):
    """
    A class representing a connection to the APNs Feedback server
    """
    def __init__(self, use_sandbox=False, **kwargs):
        super(FeedbackConnection, self).__init__(**kwargs)
        self.server = (
            'feedback.push.apple.com',
            'feedback.sandbox.push.apple.com')[use_sandbox]
        self.port = 2196

    def _chunks(self):
        BUF_SIZE = 4096
        while 1:
            data = self.read(BUF_SIZE)
            yield data
            if not data:
                break

    def items(self):
        """
        A generator that yields (token_hex, fail_time) pairs retrieved from
        the APNs feedback server
        """
        buff = ''
        for chunk in self._chunks():
            buff += chunk

            # Quit if there's no more data to read
            if not buff:
                break

            # Sanity check: after a socket read we should always have at least
            # 6 bytes in the buffer
            if len(buff) < 6:
                break

            while len(buff) > 6:
                token_length = APNs.unpacked_ushort_big_endian(buff[4:6])
                bytes_to_read = 6 + token_length
                if len(buff) >= bytes_to_read:
                    fail_time_unix = APNs.unpacked_uint_big_endian(buff[0:4])
                    fail_time = datetime.utcfromtimestamp(fail_time_unix)
                    token = b2a_hex(buff[6:bytes_to_read])

                    yield (token, fail_time)

                    # Remove data for current token from buffer
                    buff = buff[bytes_to_read:]
                else:
                    # break out of inner while loop - i.e. go and fetch
                    # some more data and append to buffer
                    break

class UnknownResponse(Exception):
    def __init__(self):
        super(UnknownResponse, self).__init__()

class UnknownError(Exception):
    def __init__(self):
        super(UnknownError, self).__init__()

class ProcessingError(Exception):
    def __init__(self):
        super(ProcessingError, self).__init__()

class InvalidTokenSizeError(Exception):
    def __init__(self):
        super(InvalidTokenSizeError, self).__init__()

class InvalidPayloadSizeError(Exception):
    def __init__(self):
        super(InvalidPayloadSizeError, self).__init__()

class InvalidTokenError(Exception):
    def __init__(self):
        super(InvalidTokenError, self).__init__()

class GatewayConnection(APNsConnection):
    """
    A class that represents a connection to the APNs gateway server
    """
    def __init__(self, use_sandbox=False, **kwargs):
        super(GatewayConnection, self).__init__(**kwargs)
        self.server = (
            'gateway.push.apple.com',
            'gateway.sandbox.push.apple.com')[use_sandbox]
        self.port = 2195

    def _get_notification(self, token_hex, payload, identifier, expiry):
        """
        Takes a token as a hex string and a payload as a Python dict and sends
        the notification
        """
        identifier_bin = identifier[:4]
        expiry_bin = APNs.packed_uint_big_endian(int(mktime(expiry.timetuple())))
        token_bin = a2b_hex(token_hex)
        token_length_bin = APNs.packed_ushort_big_endian(len(token_bin))
        payload_json = payload.json()
        payload_length_bin = APNs.packed_ushort_big_endian(len(payload_json))

        notification = ('\x01' + identifier_bin + expiry_bin + token_length_bin + token_bin
            + payload_length_bin + payload_json)

        return notification

    def send_notification(self, token_hex, payload, expiry=None):
        if expiry is None:
            expiry = datetime.now() + timedelta(30)
        
        identifier = pack('>I', getrandbits(32))
        self.write(self._get_notification(token_hex, payload, identifier, expiry))
        
        error_response = self.read(6)
        if error_response != '':
            command = error_response[0]
            status = ord(error_response[1])
            response_identifier = error_response[2:6]
            
            if command != '\x08' or response_identifier != identifier:
                raise UnknownResponse()
            
            if status == 0:
                return
            
            raise {1: ProcessingError,
                   5: InvalidTokenSizeError,
                   7: InvalidPayloadSizeError,
                   8: InvalidTokenError}.get(status, UnknownError)()

