from .services import get_client_ip, get_user_agent


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.audit_ip = get_client_ip(request)
        request.audit_user_agent = get_user_agent(request)
        return self.get_response(request)
