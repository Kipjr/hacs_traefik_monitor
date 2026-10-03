from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import router_health, service_health

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = {}
    def build():
        items=[TraefikOverview(coordinator)]
        items += [RouterSensor(coordinator,x) for x in coordinator.data["routers"]]
        items += [ServiceSensor(coordinator,x) for x in coordinator.data["services"]]
        items += [CertificateSensor(coordinator,x) for x in coordinator.data["certificates"]]
        items += [CertificateHealth(coordinator,x) for x in coordinator.data["certificates"]]
        new=[]
        for e in items:
            if e._key not in entities: entities[e._key]=e; new.append(e)
        return new
    async_add_entities(build())
    coordinator.async_add_listener(lambda: async_add_entities(build()) if build() else None)

class Base(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name=True
    def __init__(self,c,key): super().__init__(c); self._key=key; self._attr_unique_id=f"{c.entry.entry_id}_{key}"
    @property
    def device_info(self): return {"identifiers":{(DOMAIN,self.coordinator.entry.entry_id)},"name":"Traefik","manufacturer":"Traefik Labs","configuration_url":self.coordinator.client.base_url}

class TraefikOverview(Base):
    _attr_name="Status"
    def __init__(self,c): super().__init__(c,"status")
    @property
    def native_value(self): return "ONLINE"

class RouterSensor(Base):
    def __init__(self,c,x): self.protocol=x.get("protocol","http"); self.item=x.get("name","unknown"); super().__init__(c,f"router_{self.protocol}_{self.item}")
    @property
    def name(self): return f"Router {self.item} Health"
    @property
    def native_value(self): return router_health(next((x for x in self.coordinator.data["routers"] if x.get("name")==self.item and x.get("protocol")==self.protocol),{}))

class ServiceSensor(Base):
    def __init__(self,c,x): self.protocol=x.get("protocol","http"); self.item=x.get("name","unknown"); super().__init__(c,f"service_{self.protocol}_{self.item}")
    @property
    def name(self): return f"Service {self.item} Health"
    @property
    def native_value(self): return service_health(next((x for x in self.coordinator.data["services"] if x.get("name")==self.item and x.get("protocol")==self.protocol),{}))

class CertificateSensor(Base):
    _attr_device_class=SensorDeviceClass.TIMESTAMP
    def __init__(self,c,x): self.host=x["hostname"]; self.port=x["port"]; super().__init__(c,f"certificate_{self.host}_{self.port}")
    @property
    def name(self): return f"Certificate {self.host} Expiry"
    @property
    def native_value(self):
        x=next((x for x in self.coordinator.data["certificates"] if x["hostname"]==self.host and x["port"]==self.port),{})
        return datetime.fromisoformat(x["not_after"]) if x.get("not_after") and not x.get("error") else None

class CertificateHealth(Base):
    def __init__(self,c,x): self.host=x["hostname"]; self.port=x["port"]; super().__init__(c,f"certificate_health_{self.host}_{self.port}")
    @property
    def name(self): return f"Certificate {self.host} Health"
    @property
    def native_value(self):
        x=next((x for x in self.coordinator.data["certificates"] if x["hostname"]==self.host and x["port"]==self.port),{})
        if x.get("error"): return "ERROR"
        if not x.get("not_after"): return "UNKNOWN"
        expiry=datetime.fromisoformat(x["not_after"])
        if expiry <= datetime.now(expiry.tzinfo): return "EXPIRED"
        if expiry <= datetime.now(expiry.tzinfo)+timedelta(days=30): return "EXPIRING"
        return "VALID"
