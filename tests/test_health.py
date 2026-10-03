from custom_components.traefik_monitor.coordinator import service_health

def test_up(): assert service_health({'serverStatus': {'a':'UP'}}) == 'UP'
