#!/usr/bin/env python3
"""Prepare two immutable actual-macro/PART1 contexts; no RTL execution."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mask-rows',type=Path,required=True);p.add_argument('--crop',type=Path,required=True);p.add_argument('--H',type=Path,required=True);p.add_argument('--IB',type=Path,required=True);p.add_argument('--tools',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.tools));import hdc_golden as G
m=json.loads(a.mask_rows.read_text());crop=json.loads(a.crop.read_text());cm={(x['block'],x['word']):x for x in crop['records']};H=np.array([int(x,16)for x in a.H.read_text().splitlines()],dtype=np.uint32);assert len(H)==4096;hf=G.from_bits(H);contexts=[]
for tile,block,word0 in [(0,0,0),(639,148,1536)]:
 d=a.packet/'contexts'/('tile'+str(tile));d.mkdir(parents=True,exist_ok=True);cols=[]
 for col in [0,1]:
  rec=next(x for x in m['records']if x['tile']==tile and x['column']==col);src=d/Path(rec['source']).name
  actual=hashlib.sha256(src.read_bytes()).hexdigest();assert actual==rec['manifest_sha256'],('FULL_GENUINE_MASK_SHA',src)
  role=d/('mask_c'+str(col)+'.viamap.hex')
  if not role.exists():role.symlink_to(src.name)
  assert role.is_symlink()and role.readlink()==Path(src.name)
  cols.append(rec)
 shutil.copy2(a.H,d/'H4096_me_fp32.hex');shutil.copy2(a.IB,d/'resident_ib379.hex')
 sums=np.zeros((8,4,16),dtype=np.float32);rom=[];raw=[];useful=0;pad=0
 for ordinal in range(64):
  word=word0+ordinal;k=ordinal//8;slot=ordinal%8;decoded=[]
  for col in cols:
   mask=int(col['rows'][(2048+word)//8-col['physical_row_first']],16);decoded.append(sum(((mask>>(8*b+(word%8)))&1)<<b for b in range(256)))
  codes=decoded[0]|(decoded[1]<<256)
  if (block,word)in cm:
   rec=cm[(block,word)];expected=(int(rec['hex'],16)>>(128*(4*tile-rec['group_first'])))&((1<<512)-1);assert codes==expected;useful+=1
  else:assert codes==0;pad+=1
  expanded=0
  for g in range(4):
   ints=np.array([((codes>>(8*(16*g+l)))&255)for l in range(16)],dtype=np.int16);ints=np.where(ints>=128,ints-256,ints).astype(np.float32)
   cv=G.to_bf16(ints);bits=G.bits(cv)
   for lane in range(16):expanded|=int(bits[lane]>>16)<<(16*(16*g+lane))
   x=hf[8*((4*tile+g)&511)+k];sums[slot,g]=G.add(sums[slot,g],G.mul(cv,x))
  rom.append(f'{expanded:0256x}');out=G.add(G.add(sums[slot,0],sums[slot,1]),G.add(sums[slot,2],sums[slot,3]));bits=G.bits(out);value=sum(int(bits[l])<<(32*l)for l in range(16));raw.append(f'{value:0128x}')
 if tile==0:assert int(raw[0],16)&0xffffffff==0xc3174c00 and int(raw[56],16)&0xffffffff==0xc3312600
 (d/'rom_response_expected.hex').write_text('\n'.join(rom)+'\n');(d/'raw_prefix_expected.hex').write_text('\n'.join(raw)+'\n')
 contexts.append(dict(tile=tile,block=block,i_gbase=4*tile,nout=768 if tile==0 else 560,tiles=1,k=8,code_base=18432+word0,requests=64,raw_vectors=64,reference_useful_vectors=useful,genuine_padding_vectors=pad,masks=[dict(source=x['source'],canonical_filename=Path(x['source']).name,component_role='mask_c'+str(x['column'])+'.viamap.hex',sha256=x['manifest_sha256'])for x in cols]))
receipt=dict(status='PREP_NOT_RUN',contexts=contexts,scope='public macro VIAMAP contentcontexts + actual ROMleaflogic + unchanged selected-parameter PART1; no selectedROM_TILEwrapperretarget/productionphase/full512claim',gold='independenthdc_golden sequential8RNE pergroup+literalTG4tree eachK; usedcodecheckedcanonicalcrop, paddingobservedzero genuinephysicalmasks; baselineexpectedROM isneverDUTinput',input_hashes={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [a.mask_rows,a.crop,a.H,a.IB,a.tools/'hdc_golden.py']})
(a.packet/'context_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print([(x['tile'],x['requests'],x['reference_useful_vectors'],x['genuine_padding_vectors'])for x in contexts])
