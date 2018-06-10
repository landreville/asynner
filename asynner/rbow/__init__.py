from .app import make_asgi_app
from .view import AsgiViewUtility, add_asgi_view, asgi_view


__all__ = ['asgi_view']


def includeme(config):
    config.registry.registerUtility(AsgiViewUtility())
    config.add_directive('add_asgi_view', add_asgi_view)
    config.add_directive('make_asgi_app', make_asgi_app)



