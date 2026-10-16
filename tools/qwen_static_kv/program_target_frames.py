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

def main():
 p=argparse.ArgumentParser();p.add_argument('image',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=json.loads(a.image.read_text());result=encode_image(d['target'],d['epoch'],d['program'],d['descriptors']);a.out.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
