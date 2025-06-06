"""HTTP/2 APNs client using the modern provider API."""

import json
import httpx
from typing import Optional

class APNsHTTP2:
    """Simple APNs client that uses Apple's HTTP/2 provider API."""

    def __init__(self, *, use_sandbox: bool = False, cert_file: Optional[str] = None, key_file: Optional[str] = None, timeout: float = 10.0):
        self.use_sandbox = use_sandbox
        self.cert_file = cert_file
        self.key_file = key_file
        self.timeout = timeout
        self._client = httpx.Client(http2=True, verify=True, cert=(self.cert_file, self.key_file))
        self.host = ("api.push.apple.com", "api.sandbox.push.apple.com")[self.use_sandbox]

    def _endpoint(self, token: str) -> str:
        return f"https://{self.host}/3/device/{token}"

    def send_notification(self, token: str, payload: dict, topic: str, priority: int = 10) -> httpx.Response:
        headers = {
            "apns-topic": topic,
            "apns-priority": str(priority),
        }
        data = json.dumps(payload).encode("utf-8")
        url = self._endpoint(token)
        response = self._client.post(url, headers=headers, content=data, timeout=self.timeout)
        response.raise_for_status()
        return response
