from pyramid.config import Configurator


def main():
    with Configurator() as config:
        config.include('cornice')
        config.include('asynner.loopworker')
        config.include('asynner.rbow')
        config.scan('asynner.views')

        return config.make_asgi_app()


app = main()
