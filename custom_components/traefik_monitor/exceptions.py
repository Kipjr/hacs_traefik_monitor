class TraefikApiError(Exception): pass
class TraefikApiAuthError(TraefikApiError): pass
class TraefikApiConnectionError(TraefikApiError): pass
