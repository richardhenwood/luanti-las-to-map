import glob
import laspy
from itertools import chain, tee, islice, batched
from mapbuilder.dataprovider.generate import TestBlueprint, BedrockBlueprint
from mapbuilder.dataprovider.las import LasBlueprint
from mapbuilder.drafter import (
    LuantiMap, 
    within, 
    ground, 
    water, 
    surfacefill, 
    backfill, 
    notgroundwater,
    delete_classification,
    apply )


import logging
logging.basicConfig(
    level=logging.DEBUG, # Default level for the whole app
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
specific_logger = logging.getLogger('mapbuilder.drafter')
specific_logger.setLevel(logging.INFO) # Override default INFO to DEBUG for this module


laz_file = './testassets/LPine1_demo.laz'
luantibp = LasBlueprint(laz_file)
mapname = './testasset.map.sqlite'
with LuantiMap(filename=mapname, overwrite=True) as lm:
    for rawpoints in batched(luantibp.getPointsLuantiDensity(sample_resolution=1.0), 30000):
        rawpoints = delete_classification(rawpoints)

        # separate out the LAS points so we can apply separate processing
        rawpoints, groundpoints = tee(rawpoints)
        rawpoints, waterpoints = tee(rawpoints)
        rawpoints, otherpoints = tee(rawpoints)
        lasground = backfill(points=surfacefill(ground(groundpoints), largest_gap=5), z_depth=-16)
        laswater = water(waterpoints)
        lasother = notgroundwater(otherpoints)

        worldpoints = chain(lasother, laswater, lasground)
        lm.upsert(points=worldpoints,
                total_points_estimate=luantibp.total_points)


print(f"Finished writing Luanti map: {mapname}")