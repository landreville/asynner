from .connection import AsgiConnection, AsgiHttpConnection


class AsgiView(object):

    connection_class = AsgiConnection

    def __init__(self, fn):
        self._fn = fn

    def __call__(self, scope):
        async def wrap(receive, send):
            return await self._fn(self.connection_class(scope, receive, send))
        return wrap


class AsgiWebsocket(AsgiView):
    connection_class = AsgiConnection


class AsgiHttpView(AsgiView):
    connection_class = AsgiHttpConnection
