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

class Drafter():

    def __init__(self, blueprint=None):
        self.blueprint = blueprint

    def backfill(self, points):
        xyblocks = luanti.Utils.nested_dict(2, list)
        for p in points:
            xyblocks[p[0]][p[1]].append((p[2], p[3]))
        for xidx in xyblocks:
            for yidx in xyblocks[xidx]:
                floor = sorted(xyblocks[xidx][yidx], key=lambda tup: tup[0])[0]
                yield (xidx, yidx, floor[0], floor[1])
                for zidx in range(floor[0]):
                    yield (xidx, yidx, zidx, 6 ) # 6 -> "default:stone")
                    
                # floor = sorted(xyblocks[xidx][yidx])
                # yield (xidx, yidx, floor[0], floor[1])
                # for zidx in range(floor):
                #     yield (xidx, yidx, zidx, "default:stone")
                #     #p = (xidx, yidx, round(zidx / (self.blueprint.z_block_dimension * self.blueprint.z_import_scale)), "default:stone")


    def zscale(self, points, scale):
        for pt in points:
            yield pt[0], pt[1], pt[2]*scale, pt[3]

    def backfillLuantipoints(self, points):
        #lbp = blueprint.getPointsInts()
        # z = 0 is the lowest possible point. 
        for point in points:
            xblocks = self._getXYpoints(point[3])
            #xblocks = points
            #addpt = 0
            #xcount = 0
            fill_points = []
            for xidx in xblocks:
                for yidx in xblocks[xidx]:
                    # for zidx in xblocks[xidx][yidx]:
                    #     for p in xblocks[xidx][yidx][zidx]:
                    #         fill_points.extend(p)
                    floorz = min(xblocks[xidx][yidx].keys())
                    floor = xblocks[xidx][yidx][floorz][0]
                    for zidx in range(floorz):
                        p = (floor[0], floor[1], round(zidx / (self.blueprint.z_block_dimension * self.blueprint.z_import_scale)), "default:stone")
                        #blueprint.normalizedPoints.append(p)
                        #fill_points.append.append(p)
                        point[3].append(p)
                        #addpt += 1
                # xcount += 1
                # if xcount % int(len(xblocks.keys())/100) == 0:
                #     logger.info(f"backfill job {(xcount/len(xblocks.keys()))*100:6.2f}% complete")
            #blueprint.normalizedPoints.extend(fill_points)
            #blueprint.total_points = len(blueprint.normalizedPoints)
            #return blueprint
            yield point
    
    def _getXYpoints(self, points):
        #pts = blueprint.getPointsInts()
        xblocks = luanti.Utils.nested_dict(3, list)
        pidx = 0
        for pts in self.quantizedPoints(points):
            q, p = pts
            # q = pt.quantize(blueprint.x_block_dimension,
            #             blueprint.y_block_dimension,
            #             blueprint.z_block_dimension * blueprint.z_import_scale)
            xblocks[q[0]][q[1]][q[2]].append(p)
            pidx += 1
            if pidx % 10000 == 0:
                logger.info(f"quantizing into dict: {(pidx/self.blueprint.total_points)*100:3.2f}%")
        return xblocks 
        
    def quantizedPoints(self, points):
        pidx = 0
        for pt in points:
            yield (
                self.quantizePoint(pt),
                pt)
            pidx += 1
            if pidx % 50000 == 0:
                logger.info(f"quantizing points: {pidx}")
        #return points

    def ___getSuperSubBlock(self, points):
        for pts in self.quantizedPoints(points):
            qp, np = pts
            yield (
                self.superBlock(qp),
                self.subBlock(qp)
            )

    def getLuantiSuperSubBlocks(self, points):
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

    def getSuperSubBlocks(self, points):
        for pt in points:
            yield (
                self.superBlock(pt),
                self.subBlock(pt)
            )

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

    def quantizePoint(self, pt):
        npt = (
            int(round(pt[0] * self.blueprint.x_block_dimension)),
            int(round(pt[1] * self.blueprint.y_block_dimension)),
            int(round(pt[2] * self.blueprint.z_block_dimension * self.blueprint.z_import_scale)),
            pt[3])
        return npt

    def quantizePoints(self, normalpoints):
        for pt in normalpoints:
            yield self.quantizePoint(pt)

    def lossyQuantizeLuantiPoints(self, normalpoints):
        fblocks = luanti.Utils.nested_dict(3, list)
        pidx = 0
        #materials = {0: "air"}
        #materialsr = {"air": 0}
        #materialidx = 1
        for pts in self.getSuperSubBlock(normalpoints): #self.getSubSuperBlock():
            sp, sb = pts #.superblock(), .subblock()
            fblocks[sp[0]][sp[1]][sp[2]].append(sb)
            #if sb[3] not in materials:
            #    materials[materialidx] = sb[3] 
            #    materialsr[sb[3]] = materialidx
            pidx += 1
            if pidx % 10000 == 0:
                logger.info(f"quantized into luanti blocks: {pidx}")
        pidx = 0
        for mb_x in fblocks:
            for mb_y in fblocks[mb_x]:
                for mb_z in fblocks[mb_x][mb_y]:
                    deduped = self.dedupe(fblocks[mb_x][mb_y][mb_z])
                    yield (mb_x, mb_y, mb_z, deduped)  
            if mb_x % 100 == 0:
                logger.info(f"sending blocks {(pidx/len(fblocks.keys()))*100:3.2f}%")

    def dedupe(self, points):
        fblocks = luanti.Utils.nested_dict(3, list)
        dedupedpoints = []
        for pt in points:
            if pt[0] not in fblocks:
                fblocks[pt[0]] = {}
            if pt[1] not in fblocks[pt[0]]:
                fblocks[pt[0]][pt[1]] = {}
            if pt[2] in fblocks[pt[0]][pt[1]]:
                logger.info("point collision")
                continue
            dedupedpoints.append(pt)
        return dedupedpoints

    def bedrock(self, xy_dim, zbottom, ztop): #ztop is the max z
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
        xdim = 400
        ydim = 400
        # if blueprint is not None:
        #     xdim = blueprint.x_block_dimension
        #     ydim = blueprint.y_block_dimension
        for x in range(xdim):
            for y in range(ydim):
                for z in range(zbottom, ztop):
                    yield ('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
                        (x, 
                        z, 
                        y, 
                        blob_bytes))
            logger.info(f"writing bedrock {x} of {xdim}")

    def points_to_LuantiMap(isef, lblocks):
        for superblock in lblocks:
            materials, materialsr = self._getMaterials(superblock[1])
            hexblock = luanti.Utils.make_block_hex(superblock[1], materialsr)
            fhex = luanti.Utils.format_hex_block(hexblock, materials)
            version_byte = bytes([29])
            compressed_blob = zstd.ZstdCompressor(level=3).compress(fhex)
            blob_bytes = version_byte + compressed_blob
            yield ('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
                        (superblock[0][0], 
                        superblock[0][2], 
                        superblock[0][1], 
                        blob_bytes))
            pidx += 1
            if pidx % 100 == 0:
                logger.info(f"writing superblock to map.sqlite: {pidx}")

    def lblocks_to_LuantiMap(self, points):
        pidx = 0
        for superblock in points:
            materials, materialsr = self._getMaterials(superblock[1])
            hexblock = luanti.Utils.make_block_hex(superblock[1], materialsr)
            fhex = luanti.Utils.format_hex_block(hexblock, materials)
            version_byte = bytes([29])
            compressed_blob = zstd.ZstdCompressor(level=3).compress(fhex)
            blob_bytes = version_byte + compressed_blob
            yield ('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
                        (superblock[0][0], 
                        superblock[0][2], 
                        superblock[0][1], 
                        blob_bytes))
            pidx += 1
            if pidx % 100 == 0:
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



class Writer():

    def __init__(self, filename, overwrite=False):
        self.filename = filename
        self.overwrite = overwrite

    def bedrock(self, zbottom, ztop, blueprint=None): #ztop is the max z
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
        xdim = 400
        ydim = 400
        if blueprint is not None:
            xdim = blueprint.x_block_dimension
            ydim = blueprint.y_block_dimension
        with sqlite3.connect(self.filename) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                'INSERT OR REPLACE INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
                        self._bedrock_block(zbottom, ztop, blob_bytes, xdim, ydim))
            conn.commit()

    def _bedrock_block(self, zbottom, ztop, blob_bytes, xdim=400, ydim=400):
        for x in range(xdim):
            for y in range(ydim):
                for z in range(zbottom, ztop):
                    yield (x, 
                        z, 
                        y, 
                        blob_bytes)
            logger.info(f"writing bedrock {x} of {xdim}")

    def lblocks_to_LuantiMap(isef, points):
        for superblock in points:
            materials, materialsr = self._getMaterials(superblock[1])
            hexblock = luanti.Utils.make_block_hex(superblock[1], materialsr)
            fhex = luanti.Utils.format_hex_block(hexblock, materials)
            version_byte = bytes([29])
            compressed_blob = zstd.ZstdCompressor(level=3).compress(fhex)
            blob_bytes = version_byte + compressed_blob
            yield ('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
                        (superblock[0][0], 
                        superblock[0][2], 
                        superblock[0][1], 
                        blob_bytes))
            pidx += 1
            if pidx % 100 == 0:
                logger.info(f"writing superblock to map.sqlite: {pidx}")


    def write(self, points, append=False):
        if self.overwrite:
            try:
                os.remove(self.filename)
            except OSError:
                pass

        appendcmd = ""
        if append: 
            appendcmd = " IF NOT EXISTS "
        with sqlite3.connect(self.filename) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
            CREATE TABLE {appendcmd} `blocks` (
                `x` INTEGER,`y` INTEGER,`z` INTEGER,
                `data` BLOB NOT NULL,
                PRIMARY KEY (`x`, `z`, `y`))
            ''')
            pidx = 0
            for superblock in points:
                materials, materialsr = self._getMaterials(superblock[1])
                hexblock = luanti.Utils.make_block_hex(superblock[1], materialsr)
                fhex = luanti.Utils.format_hex_block(hexblock, materials)
                version_byte = bytes([29])
                compressed_blob = zstd.ZstdCompressor(level=3).compress(fhex)
                blob_bytes = version_byte + compressed_blob
                cursor.execute('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
                            (superblock[0][0], 
                            superblock[0][2], 
                            superblock[0][1], 
                            blob_bytes))
                pidx += 1
                if pidx % 100 == 0:
                    logger.info(f"writing superblock to map.sqlite: {pidx}")
            conn.commit()
        conn.close()
        logger.info(f"writing map.sqlite complete")

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
        return
        # yield ('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
        #     (x, 
        #     z, 
        #     y, 
        #     blob_bytes))
        '''
        xdim = 400
        ydim = 400
        # if blueprint is not None:
        #     xdim = blueprint.x_block_dimension
        #     ydim = blueprint.y_block_dimension
        for x in range(xdim):
            for y in range(ydim):
                for z in range(zbottom, ztop):
                    yield ('INSERT INTO blocks (x, y, z, data) VALUES (?, ?, ?, ?)',
                        (x, 
                        z, 
                        y, 
                        blob_bytes))
            logger.info(f"writing bedrock {x} of {xdim}")

        '''
        #pass

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
    