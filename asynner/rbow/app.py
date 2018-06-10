from asgiref.wsgi import WsgiToAsgi
from .interfaces import IAsgiViewUtility


def make_asgi_app(config):
    wsgi_app = config.make_wsgi_app()
    view_utility = config.registry.getUtility(IAsgiViewUtility)
    return ExtendedWsgiToAsgi(config, wsgi_app, view_utility.registrations)


class ExtendedWsgiToAsgi(WsgiToAsgi):

    def __init__(self, config, wsgi_app, protocol_router, *args, **kwargs):
        super().__init__(wsgi_app, *args, **kwargs)
        self._config = config
        self.protocol_router = protocol_router

    def __call__(self, scope, **kwargs):
        protocol = scope['type']
        path = scope['path']
        try:
            consumer = self.protocol_router[protocol][path]
        except KeyError:
            consumer = None
        if consumer is not None:
            return consumer(scope)
        return super().__call__(scope, **kwargs)

