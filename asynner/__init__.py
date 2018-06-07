"""Main entry point
"""
from pyramid.config import Configurator
from asynner.asgi import ExtendedWsgiToAsgi


def main():
    with Configurator() as config:
        config.include("cornice")
        config.include('asynner.loopworker')
        config.scan("asynner.views")
        config.include('asynner.asgi')
        config.asgi_scan('asynner.views')
        return config.make_asgi_app()


app = main()
