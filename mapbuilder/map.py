import sqlite3

from . import luanti, blueprint

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Map():

    def __init__(self, sqlitepath: str, blueprint: blueprint.Blueprint):
        self.sqlitepath = sqlitepath
        self.blueprint = blueprint
        self.mapcursor = sqlite3.connect(sqlitepath)
        
    def _points_to_blocks(self):
        pass
        