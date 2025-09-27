import sqlite3

from . import luanti, builder

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Map():

    def __init__(self, sqlitepath: str, blueprint: builder.MapFactory):
        self.sqlitepath = sqlitepath
        self.blueprint = blueprint
        self.mapcursor = sqlite3.connect(sqlitepath)
        
    def _points_to_blocks(self):
        pass
        