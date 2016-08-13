#! /usr/lical/bin/python
import json
import os
import struct
import sys
from xml.etree import ElementTree

from PIL import Image


def tree_to_dict(tree):
    d = {}
    for index, item in enumerate(tree):
        if item.tag == 'key':
            if tree[index + 1].tag == 'string':
                d[item.text] = tree[index + 1].text
            elif tree[index + 1].tag == 'true':
                d[item.text] = True
            elif tree[index + 1].tag == 'false':
                d[item.text] = False
            elif tree[index + 1].tag == 'integer':
                d[item.text] = toInt(tree[index + 1].text);
            elif tree[index + 1].tag == 'dict':
                d[item.text] = tree_to_dict(tree[index + 1])
    return d

# def toInt(value):
#     return float(value) if '.' in value else int(value)
def toInt(s):
    try:
        return int(s)
    except ValueError:
        return int(float(s))
    
def frames_from_bin(filename):
    filesize = os.path.getsize(filename);
    file =  open(filename);
    file.read(4);
    len, = struct.unpack("<B",file.read(1));
    name, = struct.unpack("<%ds" % len,file.read(len));
    
    frames = {};
    while file.tell() < filesize:
        len, = struct.unpack("<B",file.read(1));
        name, = struct.unpack("<%ds" % len,file.read(len));
        x,y,w,h,offset_x,offset_y,rotated,real_w,real_h = struct.unpack("<6HB2H",file.read(17))
    
        if rotated == 1 :
            offset_x,offset_y = offset_y,-offset_x;
            w,h=h,w;
            real_w,real_h =real_h,real_w; 
        
        frames[name] = {
             'box': 
                (
                    x,
                    y,
                    x + w,
                    y + h
                ),
            'real_sizelist': 
                [
                    real_w,
                    real_h
                ],
             "rotated":rotated==1,
             "result_box":
                (
                    toInt((real_w - w) / 2 + offset_x),
                    toInt((real_h - h) / 2 - offset_y),
                    toInt((real_w + w) / 2 + offset_x),
                    toInt((real_h + h) / 2 - offset_y),
                )
             }
    file.close();    
    
    print frames;
    return frames.items();
        
    

def frames_from_json(filename):
    json_data = open(data_filename)
    data = json.load(json_data)
    frames = {}
    for f in data['frames']:
        x = toInt(f["frame"]["x"])
        y = toInt(f["frame"]["y"])
        w = toInt(f["frame"]["h"] if f['rotated'] else f["frame"]["w"])
        h = toInt(f["frame"]["w"] if f['rotated'] else f["frame"]["h"])
        real_w = toInt(f["sourceSize"]["h"] if f['rotated'] else f["sourceSize"]["w"])
        real_h = toInt(f["sourceSize"]["w"] if f['rotated'] else f["sourceSize"]["h"])
        d = {
            'box': (
                x,
                y,
                x + w,
                y + h
            ),
            'real_sizelist': [
                real_w,
                real_h
            ],
            'result_box': (
                toInt((real_w - w) / 2),
                toInt((real_h - h) / 2),
                toInt((real_w + w) / 2),
                toInt((real_h + h) / 2)
            ),
            'rotated': f['rotated']
        }
        frames[f["filename"]] = d
    json_data.close()
    return frames.items()

def frames_from_plist(filename):
    root = ElementTree.fromstring(open(data_filename, 'r').read())
    plist_dict = tree_to_dict(root[0])
    to_list = lambda x: x.replace('{', '').replace('}', '').split(',')
    frames = plist_dict['frames'].items()
    for k, v in frames:
        frame = v
        if(plist_dict["metadata"]["format"] == 3):
            frame['frame'] = frame['textureRect']
            frame['rotated'] = frame['textureRotated']
            frame['sourceSize'] = frame['spriteSourceSize']
            frame['offset'] = frame['spriteOffset']

        rectlist = to_list(frame['frame'])
        width = toInt(rectlist[3] if frame['rotated'] else rectlist[2])
        height = toInt(rectlist[2] if frame['rotated'] else rectlist[3])
        frame['box'] = (
            toInt(rectlist[0]),
            toInt(rectlist[1]),
            toInt(rectlist[0]) + width,
            toInt(rectlist[1]) + height
        )
        real_rectlist = to_list(frame['sourceSize'])
        real_width = toInt(real_rectlist[1] if frame['rotated'] else real_rectlist[0])
        real_height = toInt(real_rectlist[0] if frame['rotated'] else real_rectlist[1])
        real_sizelist = [real_width, real_height]
        frame['real_sizelist'] = real_sizelist
        offsetlist = to_list(frame['offset'])
        offset_x = toInt(offsetlist[1] if frame['rotated'] else offsetlist[0])
        offset_y = toInt(offsetlist[0] if frame['rotated'] else offsetlist[1])

        if frame['rotated']:
            frame['result_box'] = (
                toInt((real_sizelist[0] - width) / 2 + offset_x),
                toInt((real_sizelist[1] - height) / 2 + offset_y),
                toInt((real_sizelist[0] + width) / 2 + offset_x),
                toInt((real_sizelist[1] + height) / 2 + offset_y)
            )
        else:
            frame['result_box'] = (
                toInt((real_sizelist[0] - width) / 2 + offset_x),
                toInt((real_sizelist[1] - height) / 2 - offset_y),
                toInt((real_sizelist[0] + width) / 2 + offset_x),
                toInt((real_sizelist[1] + height) / 2 - offset_y)
            )
    return frames

def gen_png_from_data(filename, ext):
    big_image = Image.open(filename + ".png")
    frames = None;
    if ext == '.plist':
       frames =  frames_from_plist(filename + ".plist")
    elif ext == '.json':
        frames =  frames_from_plist(filename + ".json")
    elif ext == '.bin':
        frames =  frames_from_bin(filename + ".bin")
    else:
        print("Wrong data format on parsing: '" + ext + "'!")
        exit(1)

    for k, v in frames:
        frame = v
        box = frame['box']
        rect_on_big = big_image.crop(box)
        real_sizelist = frame['real_sizelist']
        result_image = Image.new('RGBA', real_sizelist, (0, 0, 0, 0))
        result_box = frame['result_box']
        result_image.paste(rect_on_big, result_box, mask=0)
        if frame['rotated']:
            result_image = result_image.transpose(Image.ROTATE_90)
        if not os.path.isdir(filename):
            os.mkdir(filename)
        outfile = (filename + '/' + k).replace('gift_', '')
        print(outfile, "generated")
        result_image.save(outfile)


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print("You must pass filename as the first parameter!")
        exit(1)
    filename = sys.argv[1]
    ext = '.plist'
    if len(sys.argv) < 3:
        print("No data format passed, assuming .plist")
    ext = sys.argv[2]
    
    data_filename = filename + ext
    png_filename = filename + '.png'
    if os.path.exists(data_filename) and os.path.exists(png_filename):
        gen_png_from_data(filename, ext)
    else:
        print("Make sure you have both " + data_filename + " and " + png_filename + " files in the same directory")