import config

from util import route

def get_route():
    with (config.config.directory / config.config.routeConfig).open(encoding="utf-8") as myFile:
        loc = route.parse_route(myFile.read())
    return loc  
