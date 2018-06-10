class AsgiConnection(object):

    def __init__(self, scope, send, receive):
        self.scope = scope
        self.send = send
        self.receive = receive


class AsgiHttpConnection(AsgiConnection):
    """
    Connection intended to receive a single HTTP request and send a single HTTP Response.

    Headers will be sent automatically the first time data is sent.
    """
    def __init__(self, scope, receive, send):
        self.scope = scope
        self.send = self._wrap_send(send)
        self.receive = self._wrap_receive(receive)
        self._headers_sent = False

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

