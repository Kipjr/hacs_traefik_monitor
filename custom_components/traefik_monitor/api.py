from __future__ import annotations
import asyncio
import ssl
import aiohttp
from cryptography import x509
from .exceptions import TraefikApiError, TraefikApiAuthError, TraefikApiConnectionError

class TraefikApiClient:
    def __init__(self, host, port, use_ssl=False, verify_ssl=True, username=None, password=None):
        self.host, self.port, self.use_ssl, self.verify_ssl = host, port, use_ssl, verify_ssl
        self.auth = aiohttp.BasicAuth(username, password) if username and password else None
        self.session = None

    @property
    def base_url(self):
        return f"{'https' if self.use_ssl else 'http'}://{self.host}:{self.port}"

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get(self, path):
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl if self.use_ssl else None)
            self.session = aiohttp.ClientSession(connector=connector, auth=self.auth, timeout=aiohttp.ClientTimeout(total=10))
        try:
            async with self.session.get(self.base_url + path) as response:
                if response.status in (401, 403): raise TraefikApiAuthError()
                if response.status >= 400: raise TraefikApiError(f"HTTP {response.status}")
                return await response.json(content_type=None)
        except (TraefikApiError, TraefikApiAuthError): raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise TraefikApiConnectionError(str(err)) from err

    async def resources(self, protocol, kind):
        data = await self.get(f"/api/{protocol}/{kind}")
        return data if isinstance(data, list) else []

    async def routers(self):
        results = await asyncio.gather(*(self.resources(p, "routers") for p in ("http","tcp","udp")), return_exceptions=True)
        out = []
        for p, result in zip(("http","tcp","udp"), results):
            if isinstance(result, Exception):
                if p == "http": raise result
                continue
            out += [{**x, "protocol": p} for x in result]
        return out

    async def services(self):
        results = await asyncio.gather(*(self.resources(p, "services") for p in ("http","tcp","udp")), return_exceptions=True)
        out = []
        for p, result in zip(("http","tcp","udp"), results):
            if isinstance(result, Exception):
                if p == "http": raise result
                continue
            out += [{**x, "protocol": p} for x in result]
        return out

    async def test(self):
        await self.get("/api/http/routers")

    async def certificate(self, hostname, port=443):
        ctx = ssl.create_default_context()
        if not self.verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(self.host, port, ssl=ctx, server_hostname=hostname), 10)
        except (OSError, asyncio.TimeoutError, ssl.SSLError) as err:
            raise TraefikApiConnectionError(str(err)) from err
        try:
            obj = writer.get_extra_info("ssl_object")
            cert = x509.load_der_x509_certificate(obj.getpeercert(binary_form=True))
            try:
                san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
            except x509.ExtensionNotFound:
                san = []
            return {"hostname":hostname, "port":port, "subject":cert.subject.rfc4514_string(), "issuer":cert.issuer.rfc4514_string(), "serial_number":format(cert.serial_number,"X"), "not_after":cert.not_valid_after_utc.isoformat(), "san":san, "cipher":obj.cipher()[0], "error":None}
        finally:
            writer.close()
            await writer.wait_closed()
