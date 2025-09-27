import struct 
from collections import defaultdict

class Reference():

    mapblocks = {}
    nodes_per_block = 16 * 16 * 16

    mappings = [
        (0, "air"),
        (1, "default:stone"),
        (2, "default:stone_with_coal"),
        (3, "default:obsidian"),
        (4, "default:cobble"),
        (5, "default:dirt"),
        (6, "default:dirt_with_grass"),
        (7, "default:dirt_with_rainforest_litter"),
        (8, "default:dirt_with_dry_grass"),
        (9, "default:dry_dirt"),
        (10, "default:dry_dirt_with_dry_grass"),
        (11, "default:silver_sand"),
        (12, "default:gravel"),
        (13, "default:glass"),
        (14, "default:papyrus"),
        (15, "default:cactus"),
        (16, "default:snow"),
        (17, "default:lava_source"),
        (18, "default:lava_flowing"),
        (19, "default:water_source"),
        (20, "default:coral_pink"),
        (21, "default:ice"),
        (22, "default:permafrost"),
        (23, "default:mossycobble"),
    ]

    # https://desktop.arcgis.com/en/arcmap/latest/manage-data/las-dataset/lidar-point-classification.htm#ESRI_SECTION1_570719D89812478598FB633D71EBAD06
    classification = {
        0: (6, "default:gravel",'Never classified'),
        1: (6, "default:dirt_with_grass", 'Unassigned'),
        2: (5, 'default:dirt', 'Ground'),
        3: (6, 'default:dirt_with_grass', 'Low Vegetation'),
        4: (7, 'default:pine_sapling', 'Medium Vegetation'),
        5: (7, 'default:pine_tree', 'High Vegetation'), #TODO: add saplings
        6: (1, 'default:stone', 'Building'), 
        7: (12, 'default:gravel', 'Low Point'), 
        8: (6, 'default:dirt_with_grass', 'Reserved'), 
        9: (19, 'default:water_source', 'Water'), 
        10: (3, 'default:obsedian', 'Rail'), 
        11: (4, 'default:cobble', 'Road Surface'), 
        12: (7, 'default:dirt_with_rainforest_litter', 'Reserved'), 
        13: (13, 'default:glass', 'Wire - Guard (Shield)'), 
        14: (19, 'default:water_source', 'Wire - Conductor (Phase)'), 
        15: (19, 'default:water_source', 'Transmission Tower'), 
        16: (19, 'default:water_source', 'Wire-Structure Connector (Insulator)'), 
        17: (23, 'default:mossycobble', 'Bridge Deck'), 
        18: (11, 'default:slivr_rsand', 'High Noise'), 
        20: (5, 'default:dirt', 'Reserved'), 
    }	

    def block_convert(x, z, y):
        xb = x // 16
        xr = x - (xb * 16) 
        yb = y // 16
        yr = y - (yb * 16)
        zb = z // 16
        zr = z - (zb * 16)
        return (xb, yb, zb), (xr, yr, zr)

    def make_block_hex(xyzarr):
        nodeidx = [0] * nodes_per_block
        for xyz in xyzarr:
            idx = xyz[2] * (16 * 16) + xyz[1] * 16 + xyz[0]
            nodeidx[idx] = classification[xyz[3]][0] # 5 "default:dirt"
        hex = struct.pack(">4096H", *nodeidx)
        return hex

    def format_hex_block(hblock):
        header = bytearray()
        header.extend(b'\x00\x00\x00\x00\x00\x00\x00')  # flags, lighting, timestamp
        header.append(0)  # Name-ID Mapping version
        header.extend(struct.pack(">H", len(mappings)))
        for mid, name in mappings:
            header.extend(struct.pack(">H", mid))
            header.extend(struct.pack(">H", len(name)))
            header.extend(name.encode('utf-8'))

        header.append(2)  # content_width
        header.append(2)  # params_width

        new_param1 = b'\x00' * 4096
        new_param2 = b'\x00' * 4096
        result = bytes(header) + hblock + new_param1 + new_param2 + b"\x00\x00\x00\x00\n\x00\x00"
        return result

class Utils():

    @staticmethod
    def make_block_hex(xyzarr, materialsr):
        nodes_per_block = 16 * 16 * 16
        nodeidx = [0] * nodes_per_block
        for pt in xyzarr:
            idx = pt[1] * (16 * 16) + pt[2] * 16 + pt[0]
            nodeidx[idx] = materialsr[pt[3]]
        hex = struct.pack(">4096H", *nodeidx)
        return hex

    @staticmethod
    def format_hex_block(hblock, mappings):
        header = bytearray()
        header.extend(b'\x00\x00\x00\x00\x00\x00\x00')  # flags, lighting, timestamp
        header.append(0)  # Name-ID Mapping version
        header.extend(struct.pack(">H", len(mappings)))
        for mid, name in mappings.items():
            header.extend(struct.pack(">H", mid))
            header.extend(struct.pack(">H", len(name)))
            header.extend(name.encode('utf-8'))

        header.append(2)  # content_width
        header.append(2)  # params_width

        new_param1 = b'\x00' * 4096
        new_param2 = b'\x00' * 4096
        result = bytes(header) + hblock + new_param1 + new_param2 + b"\x00\x00\x00\x00\n\x00\x00"
        return result

    @staticmethod
    def nested_dict(n, type):
        if n == 1:
            return defaultdict(type)
        else:
            return defaultdict(lambda: Utils.nested_dict(n-1, type))
