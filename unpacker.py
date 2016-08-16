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
        x,y,w,h,offset_x,offset_y,rotated,real_w,real_h = struct.unpack("<4H2hB2H",file.read(17))
        print name, x,y,w,h,offset_x,offset_y,rotated,real_w,real_h;
        rotated = bool(rotated);
        
        frames[name] ={
            'box': (x,y,x + h if rotated else w,y + w if rotated else h),
            'real_sizelist': (real_w,real_h),
            "rotated":rotated,
            "offset":((real_w - w)/2 + offset_x,(real_h - h)/2 + offset_y)
        }
    file.close();    
    
    print frames;
    return frames.items();
        
def frames_from_plist(filename):
    root = ElementTree.fromstring(open(data_filename, 'r').read())
    plist_dict = tree_to_dict(root[0])
    to_list = lambda x: map(toInt, x.replace('{', '').replace('}', '').split(','))
    
    frames = plist_dict['frames'].items()
    for k, v in frames:
        frame = v
        if(plist_dict["metadata"]["format"] == 3):
            frame['frame'] = frame['textureRect']
            frame['rotated'] = bool(frame['textureRotated'])
            frame['sourceSize'] = frame['spriteSourceSize']
            frame['offset'] = frame['spriteOffset']
            
        x,y,w,h= to_list(frame['frame']);
        offset_x,offset_y = to_list(frame['offset']);
        real_w,real_h = to_list(frame['sourceSize']);
        rotated = bool(frame['rotated']);
        
        frame = {
            'box': (x,y,x + h if rotated else w,y + w if rotated else h),
            'real_sizelist': (real_w,real_h),
            "rotated":rotated,
            "offset":((real_w - w)/2 + offset_x,(real_h - h)/2 + offset_y)
        }
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
        temp_image = big_image.crop(box)
        if frame['rotated']:
            temp_image = temp_image.transpose(Image.ROTATE_90)
            #             temp_image = temp_image.rotate(90,0,True);
        
        result_image = Image.new('RGBA', frame['real_sizelist'], (0,0,0,0))
        result_image.paste(temp_image,frame['offset'], mask=0);
            
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