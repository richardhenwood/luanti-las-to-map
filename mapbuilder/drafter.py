from .blueprint import Blueprint #, PointXYZC
from . import luanti

import sqlite3
import os
import zstandard as zstd
import numpy

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# supernode = x,y,z
# subnode = x,y,z,material
#luantisuperblock = [(supernode_coords, [subnode])]


class LuantiMap():

    def __init__(self, filename, overwrite=False):
        self.filename = filename
        self.overwrite = overwrite

    def __enter__(self):
        if self.overwrite:
            try:
                os.remove(self.filename)
            except OSError:
                pass
        self.conn = sqlite3.connect(self.filename)
        self.cur = self.conn.cursor()
        self.cur.execute(f'''
            CREATE TABLE IF NOT EXISTS `blocks` (
                `x` INTEGER,`y` INTEGER,`z` INTEGER,
                `data` BLOB NOT NULL,
                PRIMARY KEY (`x`, `z`, `y`))
            ''')
        return self

    def upsert(self, points, total_points_estimate):
        insert_count = 0
        for upsert in self._points_to_LuantiSql(points):
            self.cur.execute(*upsert) 
            if insert_count % int(total_points_estimate/1000) == 0:
                logger.info(f"writing superblocks to map.sqlite: {(insert_count/total_points_estimate)*100:6.2f}%")
            insert_count += 1
        
    def bedrock(self, xy_dim, z_max, z_min):
        bedrockblock = []
        blockdim = 16
        for x in range(blockdim):
            for y in range(blockdim):
                for z in range(blockdim):
                    bedrockblock.append((x, y, z, "default:stone"))
        materials, materialsr = self._getMaterials(bedrockblock)
        hexblock = luanti.Utils.make_block_hex(bedrockblock, materialsr)
        fhex = luanti.Utils.format_hex_block(hexblock, materials)
        version_byte = bytes([29])
        compressed_blob = zstd.ZstdCompressor(level=3).compress(fhex)
        blob_bytes = version_byte + compressed_blob
        self.cur.execute('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
            (xy_dim[0], 
            z_max, 
            xy_dim[2], 
            blob_bytes))
        blockid = self.cur.lastrowid
        bedrockblock_count = abs((xy_dim[0]-xy_dim[2])
                        * (xy_dim[1]-xy_dim[3])
                        * (z_max - z_min))
        count = 0
        for xblock in range(xy_dim[0], xy_dim[2]):
            for yblock in range(z_min, z_max):
                for zblock in range(xy_dim[1], xy_dim[3]):
                    self.cur.execute('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
                        (xblock, yblock, zblock, blob_bytes))
                    count += 1
            logger.info(f"writing bedrock {(count/bedrockblock_count)*100}")

    def _points_to_SuperSubBlocks(self, points):
        xblocks = luanti.Utils.nested_dict(3, list)
        pidx = 0
        for p in points:
            sb = self.superBlock(p)
            sp = self.subBlock(p)
            xblocks[sb[0]][sb[1]][sb[2]].append(sp)
        for xidx in xblocks:
            for yidx in xblocks[xidx]:
                for zidx in xblocks[xidx][yidx]:
                    yield (
                        (xidx, yidx, zidx),
                        xblocks[xidx][yidx][zidx]
                    )

    def _points_to_LuantiSql(self, points):
        pidx = 0
        for superblock in self._points_to_SuperSubBlocks(points):
            materials, materialsr = self._getMaterials(superblock[1])
            hexblock = luanti.Utils.make_block_hex(superblock[1], materialsr)
            fhex = luanti.Utils.format_hex_block(hexblock, materials)
            version_byte = bytes([29])
            compressed_blob = zstd.ZstdCompressor(level=3).compress(fhex)
            blob_bytes = version_byte + compressed_blob
            yield ('INSERT INTO blocks (x, y, z, data) \
                        VALUES (?, ?, ?, ?) \
                        ON CONFLICT(x,y,z) \
                        DO UPDATE SET \
                        x=excluded.x, \
                        y=excluded.y, \
                        z=excluded.z, \
                        data=excluded.data',
                        (superblock[0][0], 
                        superblock[0][2], 
                        superblock[0][1], 
                        blob_bytes))
            pidx += 1
            if pidx % 1000 == 0:
                logger.info(f"writing superblock to map.sqlite: {pidx}")

    def _getMaterials(self, points):
        materials = {0: "air"}
        materialsr = {"air": 0}
        materialidx = 1
        for pt in points:
            if pt[3] not in materialsr:
                materials[materialidx] = pt[3] 
                materialsr[pt[3]] = materialidx
                materialidx += 1
        return materials, materialsr 

    def superBlock(self, pt):
        p = (
            int(pt[0]) // 16,
            int(pt[1]) // 16,
            int(pt[2]) // 16,
            luanti.Reference.classification[pt[3]][1]
            #pt[3]
        )
        return p

    def subBlock(self, pt):
        p = (
            int(pt[0]) % 16,
            int(pt[1]) % 16,
            int(pt[2]) % 16,
            luanti.Reference.classification[pt[3]][1]
            #pt[3] #"default:dirt"
            #mat = luanti.Reference.classification.get(pt[3])[1]
        )
        return p

    def get_origin(self):
        row = self.cur.execute("SELECT min(x), min(y) FROM blocks;").fetchone()
        return row

    def scrape_z(self, z):
        # y is what I am considering z.
        row = self.cur.execute("DELETE FROM blocks WHERE y >= ?;", (z,))
        self.conn.commit()


    def __exit__(self, *args, **kwargs):
        self.conn.commit()
        self.conn.close()

def within(point, dim):
    if (point[0] >= dim[0] and point[0] <= dim[2]
        and point[1] >= dim[1] and point[1] <= dim[3]):
        return True
    return False

def ground(points):
    for point in points:
        if point[3] == 2:
            yield point

def _surfacefillY(points, largest_gap=20):
    xyblocks = luanti.Utils.nested_dict(2, list)
    for p in points:
        xyblocks[p[0]][p[1]].append((p[2], p[3]))
    for xidx in xyblocks:
        prevy = None
        ypts = sorted(xyblocks[xidx].keys())
        if len(ypts) > 1:
            for yidx in range(len(ypts)-1):
                ya = ypts[yidx]
                yb = ypts[yidx+1]
                z, c = xyblocks[xidx][ya][0]
                if yb - ya < largest_gap:
                    for yi in range(ya, yb):
                        yield xidx, yi, z, c
        else:
            z, c = xyblocks[xidx][ypts[0]][0]
            yield xidx, ypts[0], z, c

def _surfacefillX(points, largest_gap=20):
    xyblocks = luanti.Utils.nested_dict(2, list)
    for p in points:
        xyblocks[p[1]][p[0]].append((p[2], p[3]))
    for xidx in xyblocks:
        prevy = None
        ypts = sorted(xyblocks[xidx].keys())
        if len(ypts) > 1:
            for yidx in range(len(ypts)-1):
                ya = ypts[yidx]
                yb = ypts[yidx+1]
                z, c = xyblocks[xidx][ya][0]
                if yb - ya < largest_gap:
                    for yi in range(ya, yb):
                        yield yi, xidx, z, c
        else:
            z, c = xyblocks[xidx][ypts[0]][0]
            yield ypts[0], xidx, z, c

def surfacefill(points, largest_gap=20):
    yield from _surfacefillY( 
        _surfacefillX(points, largest_gap=largest_gap),
        largest_gap=largest_gap
    )

def water(points):
    for point in points:
        if point[3] == 9:
            yield point

def notgroundwater(points):
    for point in points:
        if point[3] == 9:
            continue
        if point[3] == 2:
            continue
        yield point

def backfill(points):
    xyblocks = luanti.Utils.nested_dict(2, list)
    for p in points:
        xyblocks[p[0]][p[1]].append((p[2], p[3]))
    for xidx in xyblocks:
        for yidx in xyblocks[xidx]:
            floor = sorted(xyblocks[xidx][yidx], key=lambda tup: tup[0])[0]
            yield (xidx, yidx, floor[0], floor[1])
            for zidx in range(floor[0]):
                yield (xidx, yidx, zidx, 6 ) # 6 -> "default:stone")

def delete_classification(points, classification_number=18): # 18 is 'high noise' in LAS
    for point in points:
        if point[3] != classification_number:
            yield point
    
def apply(points, fn):
    for point in points:
        new_point = fn(point)
        yield new_point
    