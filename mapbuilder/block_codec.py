import binascii
import struct
import zstandard as zstd
import logging

''' MIT Licensed from
https://github.com/chenxu2394/Luanti-MapBlock-Codec
'''

def parse_mapblock(block):
    """
    Parse a MapBlock (after decompression) according to the serialization format.
    This parser decodes:
      - Header fields: flags, lighting_complete, timestamp,
        name-ID mappings, content_width, params_width.
      - Skips Node Data arrays.
      - Node Metadata List (version 2, as used since map format version 28).
      - Node Timers (since map format version 25), if present.
      - Static Objects, if present.
    Returns a dictionary with the parsed fields and any remaining raw data.
    """
    offset = 0
    result = {}

    # 1. Flags (u8)
    result["flags"] = block[offset]
    offset += 1

    # 2. Lighting Complete (u16, big-endian)
    result["lighting_complete"] = struct.unpack(">H", block[offset:offset+2])[0]
    offset += 2

    # 3. Timestamp (u32, big-endian)
    result["timestamp"] = struct.unpack(">I", block[offset:offset+4])[0]
    offset += 4

    # 4. Name-ID Mapping:
    result["name_id_mapping_version"] = block[offset]
    offset += 1
    num_mappings = struct.unpack(">H", block[offset:offset+2])[0]
    offset += 2
    mappings = []
    for _ in range(num_mappings):
        mapping_id = struct.unpack(">H", block[offset:offset+2])[0]
        offset += 2
        name_len = struct.unpack(">H", block[offset:offset+2])[0]
        offset += 2
        try:
            name = block[offset:offset+name_len].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            name = block[offset:offset+name_len].decode("utf-8", errors="replace")
        offset += name_len
        mappings.append({"id": mapping_id, "name": name})
    result["mappings"] = mappings

    # 5. Content Width (u8)
    result["content_width"] = block[offset]
    offset += 1
    # 6. Params Width (u8)
    result["params_width"] = block[offset]
    offset += 1

    # 7. Node Data: Read param arrays.
    content_width = result["content_width"]
    node_data = {}
    try:
        if content_width == 1:
            # Each param is 4096 bytes.
            node_data["param0"] = block[offset:offset+4096]
            offset += 4096
            node_data["param1"] = block[offset:offset+4096]
            offset += 4096
            node_data["param2"] = block[offset:offset+4096]
            offset += 4096
        elif content_width == 2:
            # param0: 4096*2 bytes, param1: 4096, param2: 4096.
            node_data["param0"] = block[offset:offset+8192]
            offset += 8192
            node_data["param1"] = block[offset:offset+4096]
            offset += 4096
            node_data["param2"] = block[offset:offset+4096]
            offset += 4096
        else:
            node_data["error"] = f"Unexpected content_width: {content_width}"
    except Exception as e:
        node_data["error"] = f"Error reading node data: {e}"
    result["node_data"] = node_data  # Now storing node data in the result

    # 8. Node Metadata List:
    # If there is exactly 7 remaining bytes, then parse them as:
    remaining = len(block) - offset
    if remaining == 7:
        # 8. Node Metadata List (empty)
        meta_version = block[offset]  # Expected to be 0
        meta_count = struct.unpack(">H", block[offset+1:offset+3])[0]  # Expected to be 0
        offset += 3
        result["metadata"] = {
            "meta_version": meta_version,
            "meta_count": meta_count,
            "entries": []
        }
        
        # 9. Node Timers (empty)
        timer_data_length = block[offset]  # Expected to be 0
        num_timers = struct.unpack(">H", block[offset+1:offset+3])[0]  # Expected to be 0
        offset += 3
        result["timers"] = []
        
        # 10. Static Objects (empty)
        static_obj_version = block[offset]  # Expected to be 0
        offset += 1
        result["static_objects"] = []
    
    return result

def decompress_blob(hex_blob):
    """
    Given a raw hex string representing a MapBlock blob (with version byte + zstd-compressed data),
    unhexlify, extract the version byte, and decompress the rest.
    Returns a tuple: (version, decompressed_data)
    """
    data = binascii.unhexlify(hex_blob)
    version = data[0]
    compressed_part = data[1:]
    
    dctx = zstd.ZstdDecompressor()
    try:
        with dctx.stream_reader(compressed_part) as reader:
            decompressed = reader.read()
    except zstd.ZstdError as e:
        import logging
        logging.error("Decompression failed: %s", e)
        return version, None
    return version, decompressed

def decode_node_ids(param0, content_width):
    """Decode the param0 array into a list of 4096 node IDs.
    For content_width == 2, each node ID is a 16-bit integer."""
    if content_width == 2:
        # There are 4096 nodes, each stored as a 2-byte unsigned short (big-endian)
        return list(struct.unpack(">4096H", param0))
    elif content_width == 1:
        # For content_width == 1, each node is a single byte.
        return list(struct.unpack(">4096B", param0))
    else:
        raise ValueError(f"Unsupported content_width: {content_width}")

def build_mapping_dict(mappings):
    """Build a dictionary mapping node IDs to node names from the mapping list."""
    # The mapping list is a list of dicts, each with keys 'id' and 'name'.
    return {entry["id"]: entry["name"] for entry in mappings}

def map_node_ids_to_names(node_ids, mapping_dict):
    """Convert a list of node IDs to a list of node names using the mapping dictionary."""
    return [mapping_dict.get(nid, f"unknown({nid})") for nid in node_ids]

def print_mapblock_layers(node_names):
    """Print the block layer by layer (y-slice). Each layer is a 16x16 grid, where y is the vertical axis.
    The data is stored in z-major order (i.e. index = z*256 + y*16 + x), so this function iterates over y as the layer coordinate."""
    for y in range(16):
        print(f"Layer y={y}:")
        for z in range(16):
            row = []
            for x in range(16):
                index = z * (16 * 16) + y * 16 + x
                row.append(node_names[index])
            print(" ".join(row))
        print("\n")  # Separate layers

def load_hex_blobs_from_txt(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

if __name__ == "__main__":
    hex_blob_file = 'hex_blobs/old_big000_0.txt'
    hex_blobs = load_hex_blobs_from_txt(hex_blob_file)

    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    for hex_blob in hex_blobs:
        print("Decoding blob: -------------------")
        version, decompressed = decompress_blob(hex_blob)
        if decompressed:
            parsed = parse_mapblock(decompressed)
            logging.info(f"Block Version (from blob header): {version}")
            for key, value in parsed.items():
                if key == "raw_remaining_data":
                    logging.info(f"{key}: {len(value)} bytes")
                else:
                    logging.info(f"{key}: {value}")
            
            # Now decode the node IDs from param0
            node_data = parsed.get("node_data", {})
            content_width = parsed.get("content_width")
            param0 = node_data.get("param0")
            if param0 is not None:
                try:
                    # Decode the node IDs from param0
                    decoded_node_ids = decode_node_ids(param0, content_width)
                    # Build the mapping dictionary from the mappings in your block
                    mapping_dict = build_mapping_dict(parsed.get("mappings", []))
                    # Convert node IDs to node names
                    node_names = map_node_ids_to_names(decoded_node_ids, mapping_dict)
                    # Group the node names into 16 layers (each 16x16)
                    layers = [node_names[i*256:(i+1)*256] for i in range(16)]
                    # Save the results into node_data for future reference
                    node_data["decoded_node_ids"] = decoded_node_ids
                    node_data["node_names"] = node_names
                    node_data["layers"] = layers

                    # (Optional) Print the layers for inspection:
                    print("\nDecoded MapBlock (by layers):")
                    print_mapblock_layers(node_names)
                except Exception as e:
                    node_data["error_decoding"] = f"Error decoding node data: {e}"
            else:
                logging.error("No param0 found in node data.")
        else:
            logging.error("Decompression failed.")
        print("\n\n")
    print("Done.")