from .blueprint import Blueprint #, PointXYZC
from . import luanti

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Drafter():

    def backfill(self, blueprint: Blueprint) -> Blueprint:
        #lbp = blueprint.getPointsInts()
        # z = 0 is the lowest possible point. 
        xblocks = self._getXYpoints(blueprint)
        addpt = 0
        xcount = 0
        fill_points = []
        for xidx in xblocks:
            for yidx in xblocks[xidx]:
                floorz = min(xblocks[xidx][yidx].keys())
                floor = xblocks[xidx][yidx][floorz][0]
                for zidx in range(floorz):
                    p = (floor[0], floor[1], zidx / (blueprint.z_block_dimension * blueprint.z_import_scale), "default:stone")
                    blueprint.normalizedPoints.append(p)
                    addpt += 1
            xcount += 1
            if xcount % int(len(xblocks.keys())/100) == 0:
                logger.info(f"backfill job {(xcount/len(xblocks.keys()))*100:6.2f}% complete")
        #blueprint.normalizedPoints.extend(fill_points)
        blueprint.total_points = len(blueprint.normalizedPoints)
        return blueprint
    
    def ____normalize(self, blueprint, pt):
        p = pt.normalize(blueprint.x_block_dimension,
                        blueprint.y_block_dimension,
                        blueprint.z_block_dimension)
        return p
    
    def _getXYpoints(self, blueprint: Blueprint):
        #pts = blueprint.getPointsInts()
        xblocks = luanti.Utils.nested_dict(3, list)
        pidx = 0
        for pts in blueprint.getQuantizedPoints():
            q, p = pts
            # q = pt.quantize(blueprint.x_block_dimension,
            #             blueprint.y_block_dimension,
            #             blueprint.z_block_dimension * blueprint.z_import_scale)
            xblocks[q[0]][q[1]][q[2]].append(p)
            pidx += 1
            if pidx % 10000 == 0:
                logger.info(f"quantizing into dict: {(pidx/blueprint.total_points)*100:3.2f}%")
        return xblocks 
        
        
