from datetime import timedelta
DOMAIN = "traefik_monitor"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SSL = "ssl"
CONF_VERIFY_SSL = "verify_ssl"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
PLATFORMS = ["sensor"]
