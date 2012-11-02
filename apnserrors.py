class PayloadTooLargeError(Exception):
    def __init__(self):
        super(PayloadTooLargeError, self).__init__()

class APNResponseError(Exception):
    def __init__(self, status, identifier):
        self.status = status
        self.identifier = identifier

    def __repr__(self):
        return "{}<identifier: {}>".format(self.__class__.__name__, self.identifier)

    def __str__(self):
        return self.__repr__()
        
class ProcessingError(APNResponseError):
    def __init__(self, identifier):
        super(ProcessingError, self).__init__(1, identifier)

class MissingDeviceTokenError(APNResponseError):
    def __init__(self, identifier):
        super(MissingDeviceTokenError, self).__init__(2, identifier)

class MissingTopicError(APNResponseError):
    def __init__(self, identifier):
        super(MissingTopicError, self).__init__(3, identifier)

class MissingPayloadError(APNResponseError):
    def __init__(self, identifier):
        super(MissingPayloadError, self).__init__(4, identifier)
        
class InvalidTokenSizeError(APNResponseError):
    def __init__(self, identifier):
        super(InvalidTokenSizeError, self).__init__(5, identifier)

class InvalidTopicSizeError(APNResponseError):
    def __init__(self, identifier):
        super(InvalidTopicSizeError, self).__init__(6, identifier)

class InvalidPayloadSizeError(APNResponseError):
    def __init__(self, identifier):
        super(InvalidPayloadSizeError, self).__init__(7, identifier)

class InvalidTokenError(APNResponseError):
    def __init__(self, identifier):
        super(InvalidTokenError, self).__init__(8, identifier)
        
class UnknownError(APNResponseError):
    def __init__(self, identifier):
        super(UnknownError, self).__init__(255, identifier)
