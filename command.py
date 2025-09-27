import glob
import laspy
from mapbuilder.converters.demo import TestBlueprint
from mapbuilder.converters.las import LasBlueprint
from mapbuilder.converters.sqlite import LuantiMapBlueprint
from mapbuilder.converters.png import PngBlueprint
from mapbuilder.drafter import Drafter

las_files = []
laz_dir = '../../3d_stuff/peaks/laz_files/*.copc.laz'
for copcfile in glob.glob(laz_dir):
    las_files.append(copcfile)


#blueprint = LasBlueprint(las_files[0])
#blueprint = LasBlueprint('testassets/LPine1_demo.laz')
blueprint = PngBlueprint('testassets/peaks.lores.png')
#blueprint.zscale(0.1)
#blueprint = TestBlueprint(datafile=None)
blueprint = Drafter().backfill(blueprint)
#blueprint_base = LuantiMapBlueprint('./testassets/superflat.map.sqlite')
#points = blueprint_base.getPointsNormalized()
#blueprint_png = architect.Blueprint('./test.png')

blueprint.write_to_sqlite('./map.sqlite', overwrite=True)


# architect = Architect(blueprint_base)
# final_blueprint = architect.combine(blueprint_from_laz)

# final_blueprint.write_to_sqlite('./map.sqlite')
