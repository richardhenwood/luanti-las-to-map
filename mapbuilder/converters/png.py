
from ..blueprint import Blueprint #, PointXYZC
from PIL import Image

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PngBlueprint(Blueprint):

    def _preprocess(self):
        with Image.open(self.datafile).convert('L') as p_bitmap:
            print('here')
            width, height = p_bitmap.size
            self.abs_x_min = 0
            self.abs_x_max = width
            self.abs_y_min = 0
            self.abs_y_max = height
            self.abs_z_min = 0
            self.abs_z_max = self._getYdelta(p_bitmap)
            self.total_points = width * height
            self.x_block_dimension = width
            self.y_block_dimension = height
            self.z_block_dimension = self.abs_z_max
    
    def _getYdelta(self, p_bitmap):
        delta = 0
        for x in range(p_bitmap.width):
            for y in range(p_bitmap.height):
                val = p_bitmap.getpixel((x, y))
                if val > delta:
                    delta = val
        return delta

    
    def getPointsNormalized(self) -> Blueprint.pointList: #list[PointXYZC]:
        points = []
        pidx = 0
        # convert('L') to flip the image because that makes 
        # the coordinate system work as expected.
        with Image.open(self.datafile).convert('L') as p_bitmap:
            for x in range(p_bitmap.width):
                for y in range(p_bitmap.height):
                    val = p_bitmap.getpixel((x, y))
                    val = val * self.z_import_scale
                    points.append((x/self.abs_x_max, y/self.abs_y_max, val/self.abs_z_max, "default:dirt"))
                    pidx += 1
            if pidx % int(self.total_points/100) == 0:
                logger.info(f"normalizing job {(pidx/self.total_points)*100:6.2f}% complete")
        return points
        #             val = p_bitmap.getpixel((x, y))
        #             if val != 145:
        #                 if val < z_min:
        #                     z_min = val
        #                 if val > z_max:
        #                     z_max = val
        #                 #print(val) 
        #                 pattern[(x, y, val)] = MATERIAL_MAP.get("dirt", 0)
        # global_size_x = p_bitmap.width + 1
        # global_size_y = p_bitmap.height + 1
        # global_size_z = z_max + 1
