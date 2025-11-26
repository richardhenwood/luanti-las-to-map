import glob
import laspy
from itertools import chain, tee
from mapbuilder.sources.generate import TestBlueprint, BedrockBlueprint
from mapbuilder.sources.las import LasBlueprint
from mapbuilder.sources.sqlite import LuantiMapBlueprint
from mapbuilder.sources.png import PngBlueprint
from mapbuilder.drafter import (
    Drafter, 
    Writer, 
    LuantiMap, 
    within, 
    ground, 
    water, 
    surfacefill, 
    backfill, 
    notgroundwater,
    delete_classification,
    apply )

las_files = []
laz_dir = '../../3d_stuff/peaks/laz_files/*.copc.laz'
for copcfile in glob.glob(laz_dir):
    las_files.append(copcfile)


if True: 
    #islandbp = PngBlueprint('testassets/peaks.lores.png')
    #laz_file = '/home/richard/my_code/3d_stuff/peaks/laz_files/USGS_LPC_ME_SouthCoastal_2020_A20_19TDJ403834.laz'
    #laz_file = 'testassets/LPine1_demo.laz'
    #laz_file = './laz_files/peaks_island_from_nationalmap.laz'
    #laz_dir = '../../3d_stuff/peaks/laz_files/*.copc.laz'
    laz_file = '../../3d_stuff/peaks/laz_files/all.laz'
    #islandbp = LasBlueprint()
    #for copcfile in glob.glob(laz_dir):
    #    islandbp.add(copcfile)
    #islandbp = LasBlueprint(las_files[4])
    #islandbp = LasBlueprint(laz_file)
    islandbp = PngBlueprint('testassets/peaks.lores.png')
    rawpoints = islandbp.getPointsLuantiDensity() #stride=100, dim=1000)
    rawpoints = delete_classification(rawpoints)
    # this moves the worldpoints up.

    rawpoints = apply(rawpoints, fn=lambda x: (x[0], x[1], round(x[2] * 1.3), x[3]))
    rawpoints = apply(rawpoints, fn=lambda x: (x[0], x[1], x[2] + (16*1), x[3]))
    #islandground = surfacefill(ground(islandpoints))
    rawpoints, groundpoints = tee(rawpoints)
    rawpoints, waterpoints = tee(rawpoints)
    rawpoints, otherpoints = tee(rawpoints)
    islandground = backfill(surfacefill(ground(groundpoints)))
    islandwater = water(waterpoints)
    islandother = notgroundwater(otherpoints)
    #islandwater = water(islandpoints)
    #islandpoints = filter(within(0.1, 0.1, 0.9, 0.9), islandpoints)

    worldpoints = chain(islandwater, islandground, islandother)
    #worldpoints = chain(islandground ,islandwater)

    #islandpoints = Drafter().backfill(islandpoints)
    #mapname = './rootstock.map.sqlite'
    mapname = './map.sqlite'
    with LuantiMap(filename=mapname, overwrite=True) as lm:
        #xorig, yorig = lm.get_origin()
        #lm.scrape_z(1)
        #worldpoints = apply(worldpoints, fn=lambda x: 
                                #    (x[0] - (xorig * 16), 
                                #     x[1] - (yorig * 16), 
                                #     x[2], x[3]))
        lm.upsert(points=worldpoints,
                total_points_estimate=islandbp.total_points)
        # lm.write(points=Drafter().bedrock(xy_dim=islandbp.getXYDim(),
        #                                     zbottom=-4,
        #                                     ztop=-1))
        lm.bedrock(xy_dim=islandbp.getXYDim(), z_max=0, z_min=-10)
        lm.bedrock(xy_dim=(0,0, 100, 100), z_max=0, z_min=-10)
    print(f"Finished writing Luanti map: {mapname}")
