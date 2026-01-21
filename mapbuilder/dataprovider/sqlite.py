
from ..blueprint import Blueprint #, PointXYZC
import zstandard
import sqlite3
import logging

logger = logging.getLogger(__name__)

class LuantiMapBlueprint(Blueprint):

    def _preprocess(self):
        if not isinstance(self.datafile, str):
            raise Exception("datafile must be a str that is the path to a single Luanti sqlite map file.")
        with sqlite3.connect(self.datafile) as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT min(x), min(y), min(z) FROM `blocks`''')
            self.abs_min_x, self.abs_min_y, self.abs_min_z = cursor.fetchone()
            cursor.execute('''SELECT max(x), max(y), max(z) FROM `blocks`''')
            self.abs_max_x, self.abs_max_y, self.abs_max_z = cursor.fetchone()
        logger.debug("unable to effeciently count blocks in sqlite file so not going to")
        self.total_points = -1

    def getPointsNormalized(self) -> Blueprint.pointList: #list[PointXYZC]:
        points = []
        with sqlite3.connect(self.datafile) as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT x, y, z, data FROM `blocks`''')
            for row in cursor.fetchall():
                blockpoints = self.expand_block(row)
                points.extend(blockpoints)
        self.total_points = len(points)
        return points

    def expand_block(self, xyzdata):
        from .block_codec import (
            parse_mapblock,
            decode_node_ids,
            build_mapping_dict,
            map_node_ids_to_names,
        )

        points = []
        bblob = xyzdata[3]
        bblob = bblob[1:] # drop the 'version' byte([29])
        blob = zstandard.ZstdDecompressor().decompress(bblob, 10000000)
        
        parsed = parse_mapblock(blob)
        
        #if len(parsed['mappings']) > 1:
        #    logger.debug("more than one node type in this block")

        # Now decode the node IDs from param0
        node_data = parsed.get("node_data", {})
        content_width = parsed.get("content_width")
        param0 = node_data.get("param0")
        mapping_dict = build_mapping_dict(parsed.get("mappings", []))
        if param0 is not None:
            try:
                # Decode the node IDs from param0
                decoded_node_ids = decode_node_ids(param0, content_width)
                # Build the mapping dictionary from the mappings in your block
                # Convert node IDs to node names
                #node_names = map_node_ids_to_names(decoded_node_ids, mapping_dict)
                # Group the node names into 16 layers (each 16x16)
                #layers = [node_names[i*256:(i+1)*256] for i in range(16)]
                # Save the results into node_data for future reference
                node_data["decoded_node_ids"] = decoded_node_ids
                #node_data["node_names"] = node_names
                #node_data["layers"] = layers

            except Exception as e:
                node_data["error_decoding"] = f"Error decoding node data: {e}"
                logger.error(f"Error decoding node data: {e}")
                raise e
        else:
            logger.error("No param0 found in node data.")
            raise Exception("No param0 found in node data.")
        #logger.debug("Assuming 0 block is ignore")
        for pidx in range(len(node_data['decoded_node_ids'])):
            n = node_data['decoded_node_ids'][pidx] 
            if n > 0:
                p = pidx
                z = p // (16 * 16) 
                z = z + (16 * 16 * (xyzdata[2] - self.abs_min_z))
                z = z / (16 * 16 * (self.abs_max_z - self.abs_min_z))
                p = p % (16 * 16)
                y = p // 16 
                y = y + (16 * 16 * (xyzdata[1] - self.abs_min_y))
                y = y / (16 * 16 * (self.abs_max_y - self.abs_min_y))
                p = p % 16 
                x = p
                x = x + (16 * 16 * (xyzdata[0] - self.abs_min_x))
                x = x / (16 * 16 * (self.abs_max_x - self.abs_min_x))
                points.append((x, y, z, mapping_dict[n]))
        return points
        
    def _unpack_hex_block(self, blob):
        pass 
        
    
