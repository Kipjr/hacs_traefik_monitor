from __future__ import annotations
import asyncio
import re
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import TraefikApiClient
from .const import *
from .exceptions import TraefikApiError, TraefikApiAuthError

HOST_RE = re.compile(r"Host(?:SNI)?\((.*?)\)", re.I)

class TraefikDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.entry = entry
        self.client = TraefikApiClient(entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data.get(CONF_SSL,False), entry.data.get(CONF_VERIFY_SSL,True), entry.data.get(CONF_USERNAME), entry.data.get(CONF_PASSWORD))
        super().__init__(hass, logger=logging.getLogger(__name__), name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL)

    async def async_shutdown(self):
        await self.client.close()

    async def _async_update_data(self):
        try:
            routers, services = await asyncio.gather(self.client.routers(), self.client.services())
            targets = set()
            for r in routers:
                if r.get("protocol") != "http" or not r.get("tls"): continue
                domains = set()
                for d in r["tls"].get("domains",[]) or []:
                    if d.get("main"): domains.add(d["main"])
                    domains.update(d.get("sans",[]) or [])
                for match in HOST_RE.findall(r.get("rule","")):
                    domains.update(x.strip().strip('"' + "`'") for x in match.split(","))
                targets.update((d,443) for d in domains if d and "*" not in d)
            async def cert(t):
                try: return await self.client.certificate(*t)
                except TraefikApiError as e: return {"hostname":t[0],"port":t[1],"error":str(e)}
            certificates = await asyncio.gather(*(cert(t) for t in sorted(targets)))
            return {"routers":routers,"services":services,"certificates":certificates}
        except TraefikApiAuthError as e: raise UpdateFailed("Authentication failed") from e
        except TraefikApiError as e: raise UpdateFailed(str(e)) from e

def service_health(service):
    s = {str(x).upper() for x in (service.get("serverStatus") or {}).values()}
    if not s: return "UNKNOWN"
    if s == {"UP"}: return "UP"
    if "UP" in s: return "DEGRADED"
    return "DOWN"

def router_health(router):
    return str(router.get("status") or "UNKNOWN").upper()
