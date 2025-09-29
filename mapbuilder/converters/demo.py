
from ..blueprint import Blueprint #, PointXYZC

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestBlueprint(Blueprint):
    def _preprocess(self):
        #size = 4096 * 16
        size = 200
        self.abs_x_min = 0
        self.abs_x_max = size
        self.abs_y_min = 0
        self.abs_y_max = size
        self.abs_z_min = -10
        self.abs_z_max = size
        self.total_points = -1
        self.x_block_dimension = size
        self.y_block_dimension = size
        self.z_block_dimension = 4

    def getPointsNormalized(self): #list[PointXYZC]:
        points = []
        size = 200
        zdepth = 4
        self.total_points = size * size * zdepth
        pidx = 0
        for x in range(size):
            for y in range(size):
                for z in range(zdepth):
                    zz = z * self.z_import_scale
                    #points.append((x/self.abs_x_max, y/self.abs_y_max, zz/zdepth, "default:stone"))
                    yield (x/self.abs_x_max, y/self.abs_y_max, zz/zdepth, "default:stone")
                    pidx += 1
            if pidx % int(self.total_points/100) == 0:
                logger.info(f"normalizing job {(pidx/self.total_points)*100:6.2f}% complete")
        return points 

class BedrockBlueprint(Blueprint):
    def _preprocess(self):
        size = 4096 * 16
        #size = 20000
        self.abs_x_min = 0
        self.abs_x_max = size
        self.abs_y_min = 0
        self.abs_y_max = size
        self.abs_z_min = -25
        self.abs_z_max = -16
        self.total_points = -1
        self.x_block_dimension = size
        self.y_block_dimension = size
        self.z_block_dimension = 4

    def getPointsLuantiDensity(self, stride=1): #list[PointXYZC]:
        points = []
        size = 1000
        #size = 4096 * 16
        zdepth = 4
        self.total_points = size * size * zdepth
        pidx = 0
        for x in range(size):
            for y in range(size):
                for z in range(self.abs_z_min, self.abs_z_max):
                    #zz = z * self.z_import_scale
                    #points.append((x/self.abs_x_max, y/self.abs_y_max, zz/zdepth, "default:stone"))
                    yield (x, y, z, "default:stone")
                    #yield (x/self.abs_x_max, y/self.abs_y_max, zz/zdepth, "default:stone")
                    pidx += 1
            # if pidx % int(self.total_points/100) == 0:
            #     logger.info(f"generating bedrock {(pidx/self.total_points)*100:6.2f}% complete")
            logger.info(f"generating bedrock {x} of {size}")
        return points 
