import venusian
from asgiref.wsgi import WsgiToAsgi

_category = 'asynner.asgi'


def includeme(config):
    config.add_directive('asgi_scan', scan_asgi)
    config.add_directive('make_asgi_app', make_asgi_app)


def make_asgi_app(config):
    wsgi_app = config.make_wsgi_app()
    return ExtendedWsgiToAsgi(config, wsgi_app, _REGISTRY.protocol_router)


def scan_asgi(config, package):
    scanner = venusian.Scanner(registry=_REGISTRY)
    scanner.scan(config.maybe_dotted(package), categories=(_category,))


class AsgiWrapper(object):

    def __init__(self, wrapped, protocol_class):
        self._wrapped = wrapped
        self._protocol_class = protocol_class

    def __call__(self, scope):
        return self._protocol_class(self._wrapped, scope)


class AsgiApp(object):

    def __init__(self, fn, scope):
        self._fn = fn
        self._scope = scope

    def __call__(self, receive, send):
        # TODO: pass new "channel" class instead of these three variables
        return self._fn(self._scope, receive, send)


class AsgiWebsocket(AsgiApp):

    def __call__(self, receive, send):
        return self._fn(self._scope, receive, send)


class AsgiView(AsgiApp):

    def __init__(self, *args, **kwargs):
        super(*args, **kwargs)
        self._headers_sent = False

    def __call__(self, receive, send):
        return self._fn(
            self._scope,
            self._wrap_receive(receive),
            self._wrap_send(send)
        )

    def _wrap_receive(self, receive):

        async def receive_imposter():
            body = b''
            more_body = True

            while more_body:
                message = await receive()
                receive()
                body += message.get('body', b'')
                more_body = message.get('more_body', False)

            return body

        return receive_imposter

    def _wrap_send(self, send):
        async def send_imposter(value):
            if not self._headers_sent:
                # TODO: allow updating headers in the view-callable
                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [
                        [b'Content-Type', b'application/json'],
                    ]
                })
                self._headers_sent = True

            return await send({
                'type': 'http.response.body',
                'body': value.encode('utf-8')
            })

        return send_imposter


class _REGISTRY(object):

    def __init__(self):
        self.protocol_router = {'http': {}, 'websocket': {}}

    def add(self, protocol, rule, fn):
        self.protocol_router[protocol][rule] = fn


_REGISTRY = _REGISTRY()


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


class _Protocol(object):
    protocol_name = None
    protocol_class = None

    def __init__(self, path):
        self._path = path

    def __call__(self, wrapped):
        def callback(scanner, name, ob):
            _REGISTRY.add(
                self.protocol_name,
                self._path,
                AsgiWrapper(wrapped, self.protocol_class)
            )
        venusian.attach(wrapped, callback, category=_category)
        return wrapped


class websocket(_Protocol):
    protocol_name = 'websocket'
    protocol_class = AsgiWebsocket


class http(_Protocol):
    protocol_name = 'http'
    protocol_class = AsgiView
