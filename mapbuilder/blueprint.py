import math
import zstandard as zstd
import sqlite3
import binascii
import struct
import laspy
import numpy
import math
import os
from typing import TypeAlias
from collections import defaultdict
from typing import List
from abc import ABC, abstractmethod
from typing import List
from PIL import Image

from . import luanti

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

''' I am treating x and y in a flat horizontal plane
    and z as the altitude above/below the plane.
    NOTE: this is not how Luanti does thing 
    so when we are writing to luanti map.sqlite
    we make the necessary conversion.
'''
class __PointXYZC():
    def __init__(self, x, y, z, c):
        self.x = x
        self.y = y
        self.z = z
        self.c = c
    
    def quantize(self, x_factor, y_factor, z_factor):
        p = PointXYZC(
            int(round(self.x * x_factor)),
            int(round(self.y * y_factor)),
            int(round(self.z * z_factor)),
            self.c
        )
        return p
    
    def normalize(self, x_factor, y_factor, z_factor):
        p = PointXYZC(
            self.x / x_factor,
            self.y / y_factor,
            self.z / z_factor,
            self.c
        )
        return p

    def subblock(self):
        p = PointXYZC(
            int(self.x) % 16,
            int(self.y) % 16,
            int(self.z) % 16,
            self.c
        )
        return p

    def superblock(self):
        p = PointXYZC(
            int(self.x) // 16,
            int(self.y) // 16,
            int(self.z) // 16,
            self.c
        )
        return p

class Blueprint(ABC):
    __slots__ = [
        'datafile',
        'luantiReference',
        'abs_x_min',
        'abs_x_max',
        'abs_y_min',
        'abs_y_max',
        'abs_z_min',
        'abs_z_max',
        'xres',
        'yres',
        'skip_index'
        'points_per_block', # points per block
        'x_block_dimension',
        'y_block_dimension',
        'z_block_dimension',
        'z_import_scale', # scale the import
        'total_points',
        'normalized_points'
        'luanti_points'
    ]
    pointList = list[(float, float, float, str)]
    normalizedPoints : pointList

    def __init__(self, datafile: str, luantiReference=None):
        self.datafile = datafile
        self.luantiReference = luantiReference
        if self.luantiReference is None:
            self.luantiReference = luanti.Reference()
        self.normalizedPoints = []
        self.luanti_points = {}
        self._preprocess()
        self.resolution = 1
        self.z_import_scale = 1.0
        self.skip_index = 1
    
    @abstractmethod
    def _preprocess(self):
        # populate the class fields
        pass

    #@abstractmethod
    def getPointsNormalized(self) -> pointList: #list[PointXYZC]:
        pass

    @abstractmethod
    def getPointsLuantiDensity(self) -> pointList: #list[PointXYZC]:
        pass

    def zscale(self, factor):
        self.z_import_scale = factor
        self.abs_z_min = self.abs_z_min * factor
        self.abs_z_max = self.abs_z_max * factor
        
    def getQuantizedPoints(self) -> pointList:
        npts = self.normalizedPoints
        if npts == []:
            npts = self.getPointsNormalized()
        self.normalizedPoints = npts
        points = []
        pidx = 0
        for pt in self.normalizedPoints:
            points.append((
                self.quantizePoint(pt),
                pt)
            )
            pidx += 1
            if pidx % 50000 == 0:
                logger.info(f"Quantizing points: {(pidx/self.total_points)*100:6.2f}%")
        return points

    def quantizePoint(self, pt):
        npt = (
            int(round(pt[0] * self.x_block_dimension)),
            int(round(pt[1] * self.y_block_dimension)),
            int(round(pt[2] * self.z_block_dimension * self.z_import_scale)),
            pt[3])
        return npt
        
    def normalizePoint(self, pt):
        npt = (
            pt[0] / self.x_block_dimension,
            pt[1] / self.y_block_dimension,
            pt[2] / (self.z_block_dimension * self.z_import_scale),
            pt[3])
        return npt

    def getSubSuperBlock(self) -> pointList:
        points = []
        for pts in self.getQuantizedPoints():
            qp, np = pts
            points.append((
                self.superBlock(qp),
                self.subBlock(qp)
            ))
        return points

    def superBlock(self, pt):
        p = (
            int(pt[0]) // 16,
            int(pt[1]) // 16,
            int(pt[2]) // 16,
            pt[3]
        )
        return p

    def subBlock(self, pt):
        p = (
            int(pt[0]) % 16,
            int(pt[1]) % 16,
            int(pt[2]) % 16,
            pt[3]
        )
        return p

    def ___getPointsInts(self) -> pointList: #list[PointXYZC]:
        npts = self.normalizedPoints
        if npts == []:
            npts = self.getPointsNormalized()
        self.normalizedPoints = npts
        #ndim = 4096 * 16
        points = []
        pidx = 0
        #for n in npts:
            ##q = n.quantize(ndim)
            #q = n.quantize(self.x_block_dimension,
                        #self.y_block_dimension,
                        #self.z_block_dimension * self.z_import_scale)
        for q in self.getQuantizedPoints():
            points.append(q)
            if pidx % 50000 == 0:
                logger.info(f"processing luanti integers: {(pidx/self.total_points)*100:6.2f}%")
            pidx += 1
        return points

    def getXYratio(self):
        x = self.abs_x_max - self.abs_x_min
        y = self.abs_y_max - self.abs_y_min
        return x/y
    
    def write_to_sqlite(self, sqlitefilename, overwrite=False):
        if overwrite:
            try:
                os.remove(sqlitefilename)
            except OSError:
                pass
        npts = self.normalizedPoints
        if npts == []:
            npts = self.getPointsNormalized()
        self.normalizedPoints = npts
        fblocks = luanti.Utils.nested_dict(3, list)
        pidx = 0
        materials = {0: "air"}
        materialsr = {"air": 0}
        materialidx = 1
        for pts in self.getSubSuperBlock():
            sp, sb = pts #.superblock(), .subblock()
            fblocks[sp[0]][sp[1]][sp[2]].append(sb)
            if sb[3] not in materials:
                materials[materialidx] = sb[3] 
                materialsr[sb[3]] = materialidx
            pidx += 1
            if pidx % 10000 == 0:
                logger.info(f"packaging into luanti blocks: {(pidx/self.total_points)*100:3.2f}%")
        with sqlite3.connect(sqlitefilename) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE `blocks` (
                `x` INTEGER,`y` INTEGER,`z` INTEGER,
                `data` BLOB NOT NULL,
                PRIMARY KEY (`x`, `z`, `y`))
            ''')
            pidx = 0
            for mb_x in fblocks:
                for mb_y in fblocks[mb_x]:
                    for mb_z in fblocks[mb_x][mb_y]:
                        hexblock = luanti.Utils.make_block_hex(fblocks[mb_x][mb_y][mb_z], materialsr)
                        fhex = luanti.Utils.format_hex_block(hexblock, materials)
                        version_byte = bytes([29])
                        compressed_blob = zstd.ZstdCompressor(level=3).compress(fhex)
                        blob_bytes = version_byte + compressed_blob
                        cursor.execute('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
                                   (mb_x, mb_z, mb_y, blob_bytes))
                        pidx += 1
                        if pidx % 10000 == 0:
                            logger.info(f"writing to map.sqlite -- {(pidx/self.total_points)*100:3.2f}%")
            conn.commit()
        conn.close()
        logger.info(f"writing map.sqlite complete")
