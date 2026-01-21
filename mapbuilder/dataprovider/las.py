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

            xsorted = numpy.sort(las.x)
            xdiff = numpy.diff(xsorted)
            xhist = numpy.histogram(xdiff, bins='auto') # use 10 bins
            # the most common delta will be ~0 because
            # we assume the data to be arranged in rows + columns
            xsecondpeak = sorted(xhist[0], reverse=True)[1]
            xresindex = numpy.where(xhist[0] == xsecondpeak)[0]
            self.xres = xhist[1][xresindex][0]

            ysorted = numpy.sort(las.y)
            ydiff = numpy.diff(ysorted)
            yhist = numpy.histogram(ydiff) # use 10 bins
            # the most common delta will be ~0 because
            # we assume the data to be arranged in rows + columns
            ysecondpeak = sorted(yhist[0], reverse=True)[1]
            yresindex = numpy.where(yhist[0] == ysecondpeak)[0]
            self.yres = yhist[1][yresindex][0]

            self.abs_x_min = numpy.min(las.x)
            self.abs_x_max = numpy.max(las.x)
            self.abs_y_min = numpy.min(las.y)
            self.abs_y_max = numpy.max(las.y)
            self.abs_z_min = numpy.min(las.z)
            self.abs_z_max = numpy.max(las.z)
            self.total_points = h.point_count
            self.x_scale = fh.header.x_scale
            self.y_scale = fh.header.y_scale
            self.z_scale = fh.header.z_scale
            
        self.x_block_dimension = int(math.sqrt(self.total_points))
        self.y_block_dimension = int(math.sqrt(self.total_points))
        self.z_block_dimension = int(self.abs_z_max - self.abs_z_min)
        logger.debug(f"finished preprocessing {fh._source.name}")
        
    def get_las_point_normalize(self, las, pidx):
        # return a normalized point x,y: 0->1
        # leave z absolute
        x = (las.x[pidx] - self.abs_x_min) / (self.abs_x_max - self.abs_x_min)
        y = (las.y[pidx] - self.abs_y_min) / (self.abs_y_max - self.abs_y_min)
        z = (las.z[pidx] - self.abs_z_min) / (self.abs_z_max - self.abs_z_min)
        c = las.classification[pidx]
        return x, y, z, Reference.classification[c][1] #"default:dirt" #las.classification[pidx]

    def _get_las_point(self, las, pidx):
        # return an integer point x,y: 0->luanti_dimension
        # leave z absolute
        luantidim = Reference().dim
        x = round(((las.points[pidx].x.min() - self.abs_x_min) / (self.abs_x_max - self.abs_x_min)) * luantidim) # (self.x_block_dimension/self.xres))
        y = round(((las.points[pidx].y.min() - self.abs_y_min) / (self.abs_y_max - self.abs_y_min)) * luantidim) # (self.y_block_dimension/self.yres))
        #z = int(((las.z[pidx] - self.abs_z_min) / (self.abs_z_max - self.abs_z_min)) / self.z_import_scale)
        z = round(las.points[pidx].z.min() * self.z_import_scale)# - self.abs_z_min) / (self.abs_z_max - self.abs_z_min)) / self.z_import_scale)
        c = las.points[pidx].classification
        return x, y, z, Reference.classification[c][1] #"default:dirt" #las.classification[pidx]

    def _las_point_xtransform(self, x):
        #fx = numpy.round(((x - self.abs_x_min) / (self.abs_x_max - self.abs_x_min)) * (10/self.xres)) # (self.y_block_dimension/self.yres))
        fx = numpy.round(((x - self.abs_x_min) / (self.abs_x_max - self.abs_x_min)) 
                * self.x_scale * self.point_size * (0.5/self.xres)) # (self.y_block_dimension/self.yres))
        return fx

    def _las_point_ytransform(self, y):
        fy = numpy.round(((y - self.abs_y_min) / (self.abs_y_max - self.abs_y_min)) 
                * self.y_scale * self.point_size * (0.5/self.xres)) # (self.y_block_dimension/self.yres))
        return fy

    def _las_point_ztransform(self, z):
        fz = numpy.round(z * self.z_import_scale)
        return fz

    def _las_point_ctransform(self, c):
        fc = Reference.classification.get(c)[1] #"default:dirt" #las.classification[pidx]
        return fc

    def within_luanti_world(self, x):
        res = ((x[:,0] >= 0) & (x[:,0] < self.luantidim) &
            (x[:,1] >= 0) & (x[:,1] < self.luantidim) &
            (x[:,2] >= 0) & (x[:,2] < self.luantidim))
        return res

    def getPointsLuantiDensity(self, stride=1, dim = None, z_import_scale=1, sample_resolution=1, batch_size=1000000): #list[PointXYZC]:
        ''' sample_resolution: 1 is highest resolution, fractions of 1 are lower resolution
        '''
        if dim is None:
            self.luantidim = Reference().dim
        self.z_import_scale = z_import_scale
        self.stride = stride
        luantipoints = None
        with laspy.open(self.datafile) as fh:
            logger.info(f"getPoints {fh._source.name}")
            las = fh.read()

            #self.point_size = las.points.point_size
            self.point_size = sample_resolution/self.xres
            f = self._las_point_xtransform
            luantix = f(las.x).astype(int)
            f = self._las_point_ytransform
            luantiy = f(las.y).astype(int)
            f = self._las_point_ztransform
            luantiz = f(las.z).astype(int)
            # f = self._las_point_ctransform
            
            luantic = numpy.array(las.classification).astype(int)

            lpts = numpy.stack((luantix, luantiy, luantiz, luantic), axis=-1)    

            # luantipoints = numpy.array(list(zip(luantix,
            #                                 luantiy,
            #                                 luantiz,
            #                                 luantic)))
        inworld = ((lpts[:,0] >= 0) & (lpts[:,0] < self.luantidim) &
            (lpts[:,1] >= 0) & (lpts[:,1] < self.luantidim) &
            (lpts[:,2] >= 0) & (lpts[:,2] < self.luantidim))

        luantipoints = lpts[inworld]
        
        #rnd_indices = numpy.random.choice(len(luantipoints)) 
        yield from luantipoints#[:1000000]
            

    def getPointsLuantiDensity_orig(self, stride=1, dim = None): #list[PointXYZC]:
        if dim is None:
            dim = Reference().dim
        self.stride = stride
        points = []
        with laspy.open(self.datafile) as fh:
            logger.info(f"getPoints {fh._source.name}")
            las = fh.read()
            for pidx in range(0, fh.header.point_count, self.stride):
            #for pidx in range(0, 10000):
                xb, yb, zb, classification = self._get_las_point(las, pidx)
                if xb > dim:
                    continue
                if yb > dim:
                    continue
                yield (xb, yb, zb, classification)
                #points.append((xb, yb, zz, classification))
                #points.append([xb, yb, zb, classification])
                    
                if pidx % int(self.total_points/50) == 0:
                    logger.info(f"reading points in Luanti density: {(pidx/self.total_points)*100:6.2f}% complete")
        yield from points 

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
                yield (xb, yb, zz, classification)
                #points.append((xb, yb, zz, classification))
                #points.append([xb, yb, zb, classification])
                    
                if pidx % int(self.total_points/50) == 0:
                    logger.info(f"reading points and normalizing: {(pidx/self.total_points)*100:6.2f}% complete")
        return points 
                    