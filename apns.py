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
from datetime import datetime
from socket import socket, timeout, AF_INET, SOCK_STREAM
from socket import error as socket_error
from struct import pack, unpack
import sys
import ssl
import select
import time
import collections, itertools
import logging
try:
    from ssl import wrap_socket, SSLError
except ImportError:
    from socket import ssl as wrap_socket, sslerror as SSLError

from _ssl import SSL_ERROR_WANT_READ, SSL_ERROR_WANT_WRITE

try:
    import json
except ImportError:
    import simplejson as json

_logger = logging.getLogger(__name__)

MAX_PAYLOAD_LENGTH = 256

NOTIFICATION_COMMAND = 0
ENHANCED_NOTIFICATION_COMMAND = 1

NOTIFICATION_FORMAT = (
     '!'   # network big-endian
     'B'   # command
     'H'   # token length
     '32s' # token
     'H'   # payload length
     '%ds' # payload
    )

ENHANCED_NOTIFICATION_FORMAT = (
     '!'   # network big-endian
     'B'   # command
     'I'   # identifier
     'I'   # expiry
     'H'   # token length
     '32s' # token
     'H'   # payload length
     '%ds' # payload
    )

ERROR_RESPONSE_FORMAT = (
     '!'   # network big-endian
     'B'   # command
     'B'   # status
     'I'   # identifier
    )

TOKEN_LENGTH = 32
ERROR_RESPONSE_LENGTH = 6
DELAY_RESEND_SECS = 0.0
SENT_BUFFER_QTY = 3000

ER_STATUS = 'status'
ER_IDENTIFER = 'identifier'

class APNs(object):
    """A class representing an Apple Push Notification service connection"""

    def __init__(self, use_sandbox=False, cert_file=None, key_file=None, enhanced=False):
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
        self.enhanced = enhanced

    @staticmethod
    def packed_uchar(num):
        """
        Returns an unsigned char in packed form
        """
        return pack('>B', num)

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
    
    @staticmethod
    def unpacked_char_big_endian(bytes):
        """
        Returns an unsigned char from a packed big-endian (network) byte array
        """
        return unpack('c', bytes)[0]

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
                key_file = self.key_file,
                enhanced = self.enhanced
            )
        return self._gateway_connection


class APNsConnection(object):
    """
    A generic connection class for communicating with the APNs
    """
    def __init__(self, cert_file=None, key_file=None, timeout=None, enhanced=False):
        super(APNsConnection, self).__init__()
        self.cert_file = cert_file
        self.key_file = key_file
        self.timeout = timeout
        self._socket = None
        self._ssl = None
        self.enhanced = enhanced
        self.connection_alive = False

    def __del__(self):
        self._disconnect();

    def _connect(self):
        # Establish an SSL connection

        # Fallback for socket timeout.
        for i in xrange(3):
            try:
                self._socket = socket(AF_INET, SOCK_STREAM)
                self._socket.settimeout(self.timeout)
                self._socket.connect((self.server, self.port))
                break
            except timeout:
                pass
            except:
                raise

        if self.enhanced:
             self._socket.setblocking(False)
             self._ssl = wrap_socket(self._socket, self.key_file, self.cert_file,
                                         do_handshake_on_connect=False)
             while True:
                 try:
                     self._ssl.do_handshake()
                     self.connection_alive = True
                     break
                 except ssl.SSLError, err:
                     if ssl.SSL_ERROR_WANT_READ == err.args[0]:
                         select.select([self._ssl], [], [])
                     elif ssl.SSL_ERROR_WANT_WRITE == err.args[0]:
                         select.select([], [self._ssl], [])
                     else:
                         raise
        else:
            # Fallback for 'SSLError: _ssl.c:489: The handshake operation timed out'
            for i in xrange(3):
                try:
                    self._ssl = wrap_socket(self._socket, self.key_file, self.cert_file)
                    break
                except SSLError, ex:
                    if ex.args[0] == SSL_ERROR_WANT_READ:
                        sys.exc_clear()
                    elif ex.args[0] == SSL_ERROR_WANT_WRITE:
                        sys.exc_clear()
                    else:
                       raise

    def _disconnect(self):
        if self._socket:
            self._socket.close()
            self._connection().close()
        self.connection_alive = False

    def _connection(self):
        if not self._ssl:
            self._connect()
        return self._ssl

    def _reconnect(self):
        _logger.info("rebuilding connection to APNS")
        self._disconnect()
        self._connect()

    def read(self, n=None):
        return self._connection().read(n)

    def write(self, string):
#         return self._connection().write(string)
        if self.enhanced: # nonblocking socket
            _, wlist, _ = select.select([], [self._connection()], [])
            if len(wlist) > 0:
                self._connection().sendall(string)
        else: # blocking socket
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
    def __init__(self, payload_size):
        super(PayloadTooLargeError, self).__init__()
        self.payload_size = payload_size

class Payload(object):
    """A class representing an APNs message payload"""
    def __init__(self, alert=None, badge=None, sound=None, category=None, custom={}, content_available=False):
        super(Payload, self).__init__()
        self.alert = alert
        self.badge = badge
        self.sound = sound
        self.category = category
        self.custom = custom
        self.content_available = content_available
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
        if self.category:
            d['category'] = self.category

        if self.content_available:
            d.update({'content-available': 1})

        d = { 'aps': d }
        d.update(self.custom)
        return d

    def json(self):
        return json.dumps(self.dict(), separators=(',',':'), ensure_ascii=False).encode('utf-8')

    def _check_size(self):
        payload_length = len(self.json())
        if payload_length > MAX_PAYLOAD_LENGTH:
            raise PayloadTooLargeError(payload_length)

    def __repr__(self):
        attrs = ("alert", "badge", "sound", "category", "custom")
        args = ", ".join(["%s=%r" % (n, getattr(self, n)) for n in attrs])
        return "%s(%s)" % (self.__class__.__name__, args)

class Frame(object):
    """A class representing an APNs message frame for multiple sending"""
    def __init__(self):
        self.frame_data = bytearray()

    def get_frame(self):
        return self.frame_data

    def add_item(self, token_hex, payload, identifier, expiry, priority):
        """Add a notification message to the frame"""
        item_len = 0
        self.frame_data.extend('\2' + APNs.packed_uint_big_endian(item_len))

        token_bin = a2b_hex(token_hex)
        token_length_bin = APNs.packed_ushort_big_endian(len(token_bin))
        token_item = '\1' + token_length_bin + token_bin
        self.frame_data.extend(token_item)
        item_len += len(token_item)

        payload_json = payload.json()
        payload_length_bin = APNs.packed_ushort_big_endian(len(payload_json))
        payload_item = '\2' + payload_length_bin + payload_json
        self.frame_data.extend(payload_item)
        item_len += len(payload_item)

        identifier_bin = APNs.packed_uint_big_endian(identifier)
        identifier_length_bin = \
                APNs.packed_ushort_big_endian(len(identifier_bin))
        identifier_item = '\3' + identifier_length_bin + identifier_bin
        self.frame_data.extend(identifier_item)
        item_len += len(identifier_item)

        expiry_bin = APNs.packed_uint_big_endian(expiry)
        expiry_length_bin = APNs.packed_ushort_big_endian(len(expiry_bin))
        expiry_item = '\4' + expiry_length_bin + expiry_bin
        self.frame_data.extend(expiry_item)
        item_len += len(expiry_item)

        priority_bin = APNs.packed_uchar(priority)
        priority_length_bin = APNs.packed_ushort_big_endian(len(priority_bin))
        priority_item = '\5' + priority_length_bin + priority_bin
        self.frame_data.extend(priority_item)
        item_len += len(priority_item)

        self.frame_data[-item_len-4:-item_len] = APNs.packed_uint_big_endian(item_len)

    def __str__(self):
        """Get the frame buffer"""
        return str(self.frame_data)

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
        if self.enhanced == True: #start error-response monitoring thread
            import threading
            self._sent_notifications = collections.deque(maxlen=SENT_BUFFER_QTY)
            self._send_lock = threading.RLock()
            self._close_read_thread = False
            self._read_error_response_worker = threading.Thread(target=self._read_error_response)
            self._read_error_response_worker.start()
            self._is_resending = False
            self._last_resent_qty = 10
            self._response_listener = None

    def _get_notification(self, token_hex, payload):
        """
        Takes a token as a hex string and a payload as a Python dict and sends
        the notification
        """
        token_bin = a2b_hex(token_hex)
        token_length_bin = APNs.packed_ushort_big_endian(len(token_bin))
        payload_json = payload.json()
        payload_length_bin = APNs.packed_ushort_big_endian(len(payload_json))

        zero_byte = '\0'
        if sys.version_info[0] != 2:
            zero_byte = bytes(zero_byte, 'utf-8')
        notification = (zero_byte + token_length_bin + token_bin
            + payload_length_bin + payload_json)

        return notification

    def _get_enhanced_notification(self, token_hex, payload, identifier, expiry):
         """
         form notification data in an enhanced format
         """
         token = a2b_hex(token_hex)
         payload = payload.json()
         fmt = ENHANCED_NOTIFICATION_FORMAT % len(payload)
         notification = pack(fmt, ENHANCED_NOTIFICATION_COMMAND, identifier, expiry,
                             TOKEN_LENGTH, token, len(payload), payload)
         return notification
         
    def send_notification(self, token_hex, payload, identifier=0, expiry=0):
        """
        in enhanced mode, send_notification may return error response from APNs if any
        """
        if self.enhanced:
            self._wait_resending(30)
            with self._send_lock:
                message = self._get_enhanced_notification(token_hex, payload,
                                                           identifier, expiry)
                self._sent_notifications.append(dict({'id': identifier, 'message': message}))
                try:
                    self.write(message)
                except socket_error as e:
                    _logger.info("sending notification with id:" + str(identifier) + " to APNS failed: " + str(type(e)) + ": " + str(e))
        
        else:
            self.write(self._get_notification(token_hex, payload))

    def _wait_resending(self, timeout):
        """
        timeout: in seconds
        """
        elapsed = 0.0
        interval = 0.01
        while elapsed < timeout:
            if not self._is_resending:
                break
            time.sleep(interval)
            elapsed += interval

    def send_notification_multiple(self, frame):
        return self.write(frame.get_frame())
    
    def register_response_listener(self, response_listener):
        self._response_listener = response_listener
    
    def close_read_thread(self):
        self._close_read_thread = True
    
    def _read_error_response(self):
        while not self._close_read_thread:
            time.sleep(0.1) #avoid crazy loop if something bad happened. e.g. using invalid certificate
            while not self.connection_alive:
                time.sleep(0.1)
            
            rlist, _, _ = select.select([self._connection()], [], [], 1)
            
            if len(rlist) > 0: # there's error response from APNs
                try:
                    buff = self.read(ERROR_RESPONSE_LENGTH)
                except socket_error as e: # APNS close connection arbitrarily
                    _logger.warning("exception occur when reading APNS error-response: " + str(type(e)) + ": " + str(e)) #DEBUG
                    self._is_resending = True
                    with self._send_lock:
                        self._reconnect()
                        current_sent_qty = len(self._sent_notifications)
                        resent_first_idx = max(current_sent_qty - self._last_resent_qty, 0)
                        self._resend_notification_by_range(resent_first_idx, current_sent_qty)
                    continue
                if len(buff) == ERROR_RESPONSE_LENGTH:
                    command, status, identifier = unpack(ERROR_RESPONSE_FORMAT, buff)
                    if 8 == command: # is error response
                        error_response = (status, identifier)
                        if self._response_listener:
                            self._response_listener(Util.convert_error_response_to_dict(error_response))
                        _logger.info("got error-response from APNS:" + str(error_response))
                        self._is_resending = True
                        with self._send_lock:
                            self._reconnect()
                            self._resend_notifications_by_id(identifier)
    
    def _resend_notifications_by_id(self, failed_identifier):
        fail_idx = Util.getListIndexFromID(self._sent_notifications, failed_identifier)
        #pop-out success notifications till failed one
        self._resend_notification_by_range(fail_idx+1, len(self._sent_notifications))
        return
    
    def _resend_notification_by_range(self, start_idx, end_idx):
        self._sent_notifications = collections.deque(itertools.islice(self._sent_notifications, start_idx, end_idx))
        self._last_resent_qty = len(self._sent_notifications)
        _logger.info("resending " + str(self._last_resent_qty) + " notifications to APNS") #DEBUG
        for sent_notification in self._sent_notifications:
            _logger.debug("resending notification with id:" + str(sent_notification['id']) + " to APNS") #DEBUG
            try:
                self.write(sent_notification['message'])
            except socket_error as e:
                _logger.debug("resending notification with id:" + str(sent_notification['id']) + " failed: " + str(type(e)) + ": " + str(e)) #DEBUG
                return
            time.sleep(DELAY_RESEND_SECS) #DEBUG
        self._is_resending = False

class Util(object):
    @classmethod
    def getListIndexFromID(this_class, the_list, identifier):
        return next(index for (index, d) in enumerate(the_list) 
                        if d['id'] == identifier)
    @classmethod
    def convert_error_response_to_dict(this_class, error_response_tuple):
        return {ER_STATUS: error_response_tuple[0], ER_IDENTIFER: error_response_tuple[1]}
