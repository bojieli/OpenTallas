#!/usr/bin/env python3
"""Encode declared HOST class8 boot images. No image contents are invented."""
from __future__ import annotations
import argparse,json
from pathlib import Path
TARGET_WORDS={1:327,2:181,3:4,4:192,5:192,6:1024,7:1024,8:1024,9:1024}
MASK64=(1<<64)-1

def encode_image(target:int,epoch:int,program:list[int],descriptors:list[int])->dict:
 for label,value,limit in [('target',target,9),('epoch',epoch,65535)]:
  if type(value) is not int or not 0<=value<=limit:raise ValueError(f'{label} out of range')
 if not 1<=len(program)<=1024:raise ValueError('program word count must be 1..1024')
 if target==0:
  if not 1<=len(descriptors)<=8:raise ValueError('ISA image requires 1..8 descriptors')
 elif len(program)!=TARGET_WORDS[target] or descriptors:raise ValueError('configuration target has wrong count or descriptors')
 if any(type(w) is not int or not 0<=w<=MASK64 for w in program+descriptors):raise ValueError('all image words must be unsigned64 integers')
 frames=[(8<<524)|1|(epoch<<8)|(len(program)<<24)|(len(descriptors)<<35)|(target<<39)]
 digest=0x51484f5354505247^target
 for desc,words in [(0,program),(1,descriptors)]:
  for address,word in enumerate(words):
   frames.append((8<<524)|2|(desc<<8)|(address<<9)|(word<<19))
   digest=(((digest<<7)|(digest>>57))&MASK64)^word^(desc<<10)^address
 frames.append((8<<524)|3)
 frames.append((8<<524)|4|(epoch<<8)|(digest<<24)|(target<<88))
 return {'target':target,'epoch':epoch,'program_words':len(program),'descriptor_words':len(descriptors),'digest':f'{digest:016x}','frames528':[f'{f:0132x}' for f in frames]}


def encode_boot_bundle(epoch:int,images:list[dict])->dict:
 if len(images)!=10:raise ValueError('boot bundle requires targets0..9 exactly once')
 indexed={}
 for image in images:
  target=image['target']
  if type(target) is not int or not 0<=target<=9 or target in indexed:raise ValueError('unsupported or duplicate boot target')
  if image.get('epoch',epoch)!=epoch:raise ValueError('all images must use one installed epoch')
  indexed[target]=image
 order=list(range(1,10))+[0]
 encoded=[encode_image(t,epoch,indexed[t]['program'],indexed[t]['descriptors']) for t in order]
 return {'epoch':epoch,'target_order':order,'images':encoded,'frames528':[f for image in encoded for f in image['frames528']]}

def main():
 p=argparse.ArgumentParser();p.add_argument('image',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=json.loads(a.image.read_text());result=encode_boot_bundle(d['epoch'],d['images']) if 'images' in d else encode_image(d['target'],d['epoch'],d['program'],d['descriptors']);a.out.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
