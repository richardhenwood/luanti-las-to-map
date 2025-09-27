from ..blueprint import Blueprint #, #PointXYZC
import laspy
import numpy
import math
from ..luanti import Reference

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LasBlueprint(Blueprint):

    def _preprocess(self):
        with laspy.open(self.datafile) as fh:
            logger.debug(f"preprocessing {fh._source.name}")
            h = fh.header
            # we cannot trust header min/max values.
            # i.e. self.abs_x_min = h.x_min
            las = fh.read()
            xmax = numpy.max(las.x)

            self.abs_x_min = numpy.min(las.x)
            self.abs_x_max = numpy.max(las.x)
            self.abs_y_min = numpy.min(las.y)
            self.abs_y_max = numpy.max(las.y)
            self.abs_z_min = numpy.min(las.z)
            self.abs_z_max = numpy.max(las.z)
            self.total_points = h.point_count
        logger.debug(f"finished preprocessing {fh._source.name}")
        self.x_block_dimension = int(math.sqrt(self.total_points))
        self.y_block_dimension = int(math.sqrt(self.total_points))
        self.z_block_dimension = int(self.abs_z_max - self.abs_z_min)
        
    def get_las_point(self, las, pidx):
        # return a normalized point x,y: 0->1
        # leave z absolute
        x = (las.x[pidx] - self.abs_x_min) / (self.abs_x_max - self.abs_x_min)
        y = (las.y[pidx] - self.abs_y_min) / (self.abs_y_max - self.abs_y_min)
        z = (las.z[pidx] - self.abs_z_min) / (self.abs_z_max - self.abs_z_min)
        c = las.classification[pidx]
        return x, y, z, Reference.classification[c][1] #"default:dirt" #las.classification[pidx]

    def getPointsNormalized(self) -> Blueprint.pointList:
        points = []
        with laspy.open(self.datafile) as fh:
            logger.info(f"getPoints {fh._source.name}")
            las = fh.read()
            for pidx in range(fh.header.point_count):
                xb, yb, zb, classification = self.get_las_point(las, pidx)
                #c = luanti.Reference.classification[classification][1]
                #c = "default:dirt"
                zz = zb * self.z_import_scale
                points.append((xb, yb, zz, classification))
                #points.append([xb, yb, zb, classification])
                    
                if pidx % int(self.total_points/50) == 0:
                    logger.info(f"reading points and normalizing: {(pidx/self.total_points)*100:6.2f}% complete")
        return points 
                    