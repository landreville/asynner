import venusian
from zope.interface import implementer


from .interfaces import IAsgiViewUtility
from .wrapper import AsgiHttpView, AsgiWebsocket


_sentinel = object()


_default_view_wrappers = {
    'websocket': AsgiWebsocket,
    'http': AsgiHttpView,
}


def add_asgi_view(config, package, path, protocol='http', asgi_view_wrapper=_sentinel):

    view_callable = config.maybe_dotted(package)

    if asgi_view_wrapper is _sentinel:
        asgi_view_wrapper = _default_view_wrappers[protocol]

    if asgi_view_wrapper is not None:
        view_callable = asgi_view_wrapper(view_callable)

    config.registry.getUtility(IAsgiViewUtility).register(
        path,
        protocol,
        view_callable
    )


class asgi_view(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def _register(self, scanner, name, wrapped):
        scanner.config.add_asgi_view(wrapped, *self.args, **self.kwargs)

    def __call__(self, wrapped):
        venusian.attach(wrapped, self._register)
        return wrapped


@implementer(IAsgiViewUtility)
class AsgiViewUtility(object):

    def __init__(self):
        self.registrations = {'http': {}, 'websocket': {}}

    def register(self, path, protocol, fn):
        self.registrations[protocol][path] = fn
