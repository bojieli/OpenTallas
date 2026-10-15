#!/usr/bin/env python3
"""Lower actual expanded quarter-bridge controls to native catalogue/host CSR."""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path

def load_controls(path:Path,cycles:int):
 controls={}
 for line in path.read_text().splitlines():
  entry=json.loads(line);owner=entry['owner'];cycle=entry['cycle'];word=int(entry['word'],16)
  rank,qid=owner[1:].split('q');rank,qid=int(rank),int(qid)
  if not 0<=rank<256 or qid not in range(4) or not 0<=cycle<cycles:
   raise ValueError('control identity/cycle outside declared programme')
  if not 0<=word<(1<<(49 if qid==0 else 30)):raise ValueError('control reserved bits nonzero')
  schedule=controls.setdefault(owner,{})
  if cycle in schedule:raise ValueError('duplicate/conflicting cycle record')
  schedule[cycle]=word
 return controls

def encode(schedule:dict[int,int],qid:int,cycles:int,banks:int):
 if not 1<=banks<=12 or not 0<cycles<=640*banks or qid not in range(4):
  raise ValueError('actual catalogue/host descriptor capacity exceeded; increase banks explicitly')
 words=[0]*math.ceil(cycles/10)
 for cycle,control in schedule.items():
  if not 0<=cycle<cycles or not 0<=control<1<<(49 if qid==0 else 30):raise ValueError('invalid control')
  words[cycle//10]|=control<<(49*(cycle%10))
 # Independently unpack every operation, including explicitly absent zero slots.
 for cycle in range(cycles):
  assert (words[cycle//10]>>(49*(cycle%10)))&((1<<49)-1)==schedule.get(cycle,0)
 frames=[];csr=[{'op':'write32','address_hex':'f20','data_hex':f'{56+qid:08x}'}]
 for index,word in enumerate(words):
  assert word>>490==0
  for half in range(2):
   fragment=(word>>(256*half))&((1<<256)-1)
   frames.append({'target':56+qid,'address':index*2+half,'data_hex':f'{fragment:064x}'})
   for piece in range(8):csr.append({'op':'write32','address_hex':'f24','data_hex':f'{fragment>>(32*piece)&0xffffffff:08x}'})
  csr.append({'op':'idle_core_edges','edges':2,'anchor':'after acknowledgement of second frame finalF24'})
 csr.extend([{'op':'write32','address_hex':'f28','data_hex':f'{cycles<<12:08x}'},
             {'op':'write32','address_hex':'f2c','data_hex':'00000001'},
             {'op':'idle_core_edges','edges':banks*64+2,'anchor':'after descriptorF2C acknowledgement'}])
 return {'banks':banks,'capacity_cycles':640*banks,'base':0,'limit':cycles,'loops':1,
         'catalogue_hex':[f'{w:0128x}' for w in words],'frames':frames,'csr_programming_plan':csr,
         'local_launch_to_control_output_edges':5,'local_launch_to_bridge_capture_edges':6,
         'global_launch':'caller-owned C10 afterallparticipating nativequad/VM/bridge descriptorsready'}

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--expanded',type=Path,required=True);ap.add_argument('--cycles',type=int,required=True)
 ap.add_argument('--banks',type=int,default=2);ap.add_argument('--rank',type=int,required=True)
 ap.add_argument('--qid',type=int,choices=range(4),required=True);ap.add_argument('--profile-scope',required=True)
 ap.add_argument('--out',type=Path,required=True);ap.add_argument('--catalogue-hex',type=Path)
 a=ap.parse_args();all_controls=load_controls(a.expanded,a.cycles)
 owner=f'd{a.rank}q{a.qid}'
 image=encode(all_controls.get(owner,{}),a.qid,a.cycles,a.banks)
 image.update(owner=owner,profile_scope=a.profile_scope,source_sha256=hashlib.sha256(a.expanded.read_bytes()).hexdigest())
 a.out.write_text(json.dumps(image,indent=2)+'\n')
 if a.catalogue_hex:a.catalogue_hex.write_text('\n'.join(image['catalogue_hex'])+'\n')
if __name__=='__main__':main()
