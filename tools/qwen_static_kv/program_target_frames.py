#!/usr/bin/env python3
"""Encode declared HOST class8 boot images. No image contents are invented."""
from __future__ import annotations
import argparse,json
from pathlib import Path
TARGET_WORDS={1:327,2:181,3:4,4:192,5:192,6:1024,7:1024,8:1024,9:1024,
 # KVJ-G2b 10-17: the static KV die's dispatcher targets (qkd_static_kv_boot_dispatch DIECFG/LINKCFG/ESCFG=1):
 # 10 = pre-boot die configuration (32 ECTL + NRST 43 reset delays + seal), 11 = link-end calendar (2*32+2),
 # 12 = PC chain players' constants, 13 = join4 beat calendar (8 segments)
 10:32+43+2,11:66,12:1024,13:8}
# MU-KV-BOOT 10-19: qkd_static_kv_boot_dispatch_mu MU 1 + qkd_static_kv_layer_programme_mu: target 1 in the MU form
# (rows, digest, epoch, GAP[4][36] at 326..469, seal at 470)
TARGET_WORDS_MU={**TARGET_WORDS,1:471}
# MU-KV-TOKLIST 10-19 (mu='toklist'): target 1 = rows, digest, epoch, header at 326 {ntok3,ntok2,ntok1,ntok0}, 12 (ntok1 +
# ntok2 + ntok3) list words, seal: its count follows from the header (328 + NW <= 1,024)
def target1_words_toklist(program:list[int])->int:
 h=program[326] if len(program)>326 else 0
 return 328+12*(((h>>8)&255)+((h>>16)&255)+((h>>24)&255))
MAX_TARGET=13
PREBOOT=(10,)            # pass 1 (POR, unaligned release): loaded alone, then the HOST re-asserts the functional resets
OPTIONAL=(10,11,12,13)
MASK64=(1<<64)-1

def encode_image(target:int,epoch:int,program:list[int],descriptors:list[int],mu:bool=False)->dict:
 words=TARGET_WORDS_MU if mu else TARGET_WORDS
 if mu=='toklist':words={**TARGET_WORDS_MU,1:target1_words_toklist(program) if target==1 else 0}
 for label,value,limit in [('target',target,MAX_TARGET),('epoch',epoch,65535)]:
  if type(value) is not int or not 0<=value<=limit:raise ValueError(f'{label} out of range')
 if not 1<=len(program)<=1024:raise ValueError('program word count must be 1..1024')
 if target==0:
  if not 1<=len(descriptors)<=8:raise ValueError('ISA image requires 1..8 descriptors')
 elif len(program)!=words[target] or descriptors:raise ValueError('configuration target has wrong count or descriptors')
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


def encode_boot_bundle(epoch:int,images:list[dict],mu:bool=False)->dict:
 indexed={}
 for image in images:
  target=image['target']
  if type(target) is not int or not 0<=target<=MAX_TARGET or target in indexed:raise ValueError('unsupported or duplicate boot target')
  if image.get('epoch',epoch)!=epoch:raise ValueError('all images must use one installed epoch')
  indexed[target]=image
 if any(t not in indexed for t in range(10)):raise ValueError('boot bundle requires targets0..9 exactly once')
 # dispatcher order (KVJ-G2b): pass 1 = [10] (pre-boot die cfg, only as the first image after reset); pass 2 =
 # 1..9, 11, 12, 13, 0 (the ISA target 0 last); targets 10..13 are optional (a die without DIECFG/LINKCFG/ESCFG)
 pre=[t for t in PREBOOT if t in indexed]
 order=list(range(1,10))+[t for t in (11,12,13) if t in indexed]+[0]
 encoded=[encode_image(t,epoch,indexed[t]['program'],indexed[t]['descriptors'],mu) for t in pre+order]
 out={'epoch':epoch,**({'layer_form':'MU'} if mu else {}),'target_order':pre+order,'images':encoded,'frames528':[f for image in encoded for f in image['frames528']]}
 if pre:
  n=sum(len(image['frames528']) for image in encoded[:len(pre)])
  out['passes']=[{'targets':pre,'frames':n,'then':'HOST re-asserts and releases the functional resets (die cfg kept, POR-reset only)'},
                 {'targets':order,'frames':len(out['frames528'])-n}]
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('image',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=json.loads(a.image.read_text());result=encode_boot_bundle(d['epoch'],d['images']) if 'images' in d else encode_image(d['target'],d['epoch'],d['program'],d['descriptors']);a.out.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
