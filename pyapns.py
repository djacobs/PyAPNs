from datetime import datetime
from socket import socket, AF_INET, SOCK_STREAM
from struct import pack, unpack

import simplejson
import ssl

class APNs(object):
    """A class representing an Apple Push Notification service connection"""
    
    @classmethod
    def byte_string_to_hex(cls, bstr):
        """
        Convenience method for converting a byte string to its hex representation
        """
        return ''.join(['%02x' % i for i in unpack('%iB' % len(bstr), bstr)])
    
    @classmethod
    def byte_string_from_hex(cls, hstr):
        """
        Convenience method for converting a byte string from its hex representation
        """
        byte_array = []
        
        # Make sure input string has an even number of hex characters
        # (2 hex chars = 1 byte). Add leading zero if needed.
        if len(hstr) % 2:
            hstr = '0' + hstr
        
        for i in range(0, len(hstr)/2):
            byte_hex = hstr[i*2:i*2+2]
            byte = int(byte_hex, 16)
            byte_array.append(byte)
        return pack('%iB' % len(byte_array), *byte_array)
    
    @classmethod
    def packed_ushort_big_endian(cls, num):
        """
        Returns an unsigned short in packed big-endian (network) form
        """
        return pack('>H', num)
    
    @classmethod
    def unpacked_ushort_big_endian(cls, bytes):
        """
        Returns an unsigned short from a packed big-endian (network) byte array
        """
        return unpack('>H', bytes)[0]
    
    @classmethod
    def packed_uint_big_endian(cls, num):
        """
        Returns an unsigned int in packed big-endian (network) form
        """
        return pack('>I', num)
    
    @classmethod
    def unpacked_uint_big_endian(cls, bytes):
        """
        Returns an unsigned int from a packed big-endian (network) byte array
        """
        return unpack('>I', bytes)[0]

    def __init__(self, is_test=False, cert_file=None, key_file=None):
        """Set is_test to True to use the sandbox (test) APNs servers. Default is False."""
        super(APNs, self).__init__()
        self.is_test    = is_test
        self.cert_file  = cert_file
        self.key_file   = key_file
        self._feedback_connection = None
        self._gateway_connection = None
    
    @property
    def feedback_server(self):
        if not self._feedback_connection:
            self._feedback_connection = FeedbackConnection(
                is_test   = self.is_test, 
                cert_file = self.cert_file, 
                key_file  = self.key_file
            )
        return self._feedback_connection
    
    @property
    def gateway_server(self):
        if not self._gateway_connection:
            self._gateway_connection = GatewayConnection(
                is_test   = self.is_test, 
                cert_file = self.cert_file, 
                key_file  = self.key_file
            )
        return self._gateway_connection
    
class APNsConnection(object):
    """
    A generic connection class for communicating with the APNs
    """
    def __init__(self, cert_file=None, key_file=None):
        super(APNsConnection, self).__init__()
        self.cert_file   = cert_file
        self.key_file    = key_file
        self._connection = None
    
    def __del__(self):
        self._disconnect();
    
    def _connect(self):
        # Establish an SSL connection
        self._connection = ssl.wrap_socket(
            socket(AF_INET, SOCK_STREAM), 
            keyfile=self.key_file, 
            certfile=self.cert_file
        )
        self._connection.connect((self.server, self.port))
    
    def _disconnect(self):
        if self._connection:
            socket = self._connection.unwrap()
            socket.close()
    
    def connection(self):
        if not self._connection:
            self._connect()
        return self._connection
    
    

class FeedbackConnection(APNsConnection):
    """
    A class representing a connection to the APNs Feedback server
    """
    def __init__(self, is_test=False, **kwargs):
        super(FeedbackConnection, self).__init__(**kwargs)
        self.server = ('feedback.push.apple.com', 'feedback.sandbox.push.apple.com')[is_test]
        self.port = 2196
    
    def _chunks(self):
        BUF_SIZE = 4096
        conn = self.connection()
        while 1:
            data = conn.recv(BUF_SIZE)
            yield data
            if not data:
                break
    
    def items(self):
        """
        A generator that yields (token_hex, fail_time) pairs retrieved from the APNs feedback server
        """
        buff = ''
        for chunk in self._chunks():
            # print "Reading %u bytes of data into buffer" % len(chunk)
            buff += chunk
            # print "Buffer length: %u" % len(buff)
            
            # Quit if there's no more data to read
            if not buff: 
                break
            
            # Sanity check: after a socket read we should always have at least
            # 6 bytes in the buffer
            if len(buff) < 6:
                # print "ERROR: buffer length after socket read: %u" % len(buff)
                break
            
            while len(buff) > 6:
                token_length = APNs.unpacked_ushort_big_endian(buff[4:6])
                bytes_to_read = 6 + token_length
                if len(buff) >= bytes_to_read:
                    fail_time_unix  = APNs.unpacked_uint_big_endian(buff[0:4])
                    fail_time       = datetime.utcfromtimestamp(fail_time_unix)
                    token           = APNs.byte_string_to_hex(buff[6:bytes_to_read])
                    
                    # print "%s failed at %s" % (token, str(fail_time))
                    yield (token, fail_time)
                                            
                    # Remove data for current token from buffer
                    buff = buff[bytes_to_read:]
                    # print "Deleted %u bytes from buffer, %u bytes left" % (bytes_to_read, len(buff))
                else:
                    # print "Need %u bytes, only %u left in buffer" % (bytes_to_read, len(buff))
                    # break out of inner while loop - i.e. go and fetch
                    # some more data and append to buffer
                    break

class GatewayConnection(APNsConnection):
    """
    A class that represents a connection to the APNs gateway server
    """
    def __init__(self, is_test=False, **kwargs):
        super(GatewayConnection, self).__init__(**kwargs)
        self.server = ('gateway.push.apple.com', 'gateway.sandbox.push.apple.com')[is_test]
        self.port = 2195
    
    def send_notification(self, token_hex, payload):
        """Takes a token as a hex string and a payload as a Python dict and sends the notification"""
        token_bin           = APNs.byte_string_from_hex(token_hex)
        token_length_bin    = APNs.packed_ushort_big_endian(len(token_bin))
        payload_json        = simplejson.dumps(payload, separators=(',',':'))
        payload_length_bin  = APNs.packed_ushort_big_endian(len(payload_json))
        
        notification = '\0' + token_length_bin + token_bin + payload_length_bin + payload_json
        
        self.connection().send(notification)

