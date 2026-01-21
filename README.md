# luanti-las-to-map

Convert LAS lidar data to a Luanti map

A package to convert LAS, TIF, and PNG files to Luanti maps.

inspired by: 
https://github.com/chenxu2394/Luanti-MapBlock-Codec

## Design

At a high level this library converts a point cloud into a Luanti map file.
Point values must be of the form (int, int, int) and are expected to be 
(0 <= point int < 4096*16). The point cloud can be written to a new Luanti 
map file or merged with an existing Luanti map.

Data providers emit points in this form from raw data files. Provider file types include: 
 + LAS/LAZ
 + Png
 + Luanti Sqlite
 + python code that emits a point.

LAS/LAZ is farily well tested.

## Installation

```bash
pip install luanti-las-to-map
```

## Where to find Lidar data

(https://www.usgs.gov/faqs/what-lidar-data-and-where-can-i-download-it)
(https://www.data.gov.uk/dataset/f0db0249-f17b-4036-9e65-309148c97ce4/national-lidar-programme)

## Usage

See the example [example_build.py](./example_build.py).
[map_meta.txt](./map_meta.txt.asuna) is an example file as a starting
point if you want to create a Asuna based game with your map.

## Known Problems

 + a bug exists in the luanti block merge code.
 + progress mesaure is not working.

 + the material system is poorly design.
 + the sqlite dataprovider is not tested.
 + the png dataprovider is not well tested.
 + `map_meta.txt.asuna` example is sub-optimal
