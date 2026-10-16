#!/usr/bin/env python3
"""Drive the CP512 Run builder from declared component boundary vectors.

Inputs remain declared FIELD/retained-history fixtures. This proves descriptor
packing into the actual CP VM pins, never native FIELD producer qualification.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_suhc')]
import su_gate as S

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--native-layout',action='store_true',help='use actual canonical4816/4848/4880 rows and descriptor12336/12352')
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 raw=[int(v,16)for v in (a.input/'in.mem').read_text().split()]
 if len(raw)!=256:raise ValueError('two full512-dimensional slots required')
 r=S.Run(S.SHAPES['full']);slots=[];descriptors=[]
 for epoch in range(2):
  beats=raw[128*epoch:128*(epoch+1)]
  kv=np.asarray([(b>>(32*k))&0xffffffff for b in beats for k in range(4)],np.uint32).view(np.float32)
  sc=np.asarray([(b>>(128+32*k))&0xffffffff for b in beats for k in range(4)],np.uint32).view(np.float32)
  result=r.cp_slot(kv,sc,0x10002,epoch,pool=bool(epoch),previous=slots[0]if epoch else None)
  slots.append((kv,sc));descriptors.append(result['descriptor_base'])
 expected=[int(v,16)for v in(a.input/'expected.mem').read_text().split()]
 rows=[S.pack(expected[j:j+4],128)for j in range(0,128,4)]
 if rows!=[r.exp[result['output_base']+j]for j in range(32)]:raise ValueError('independent CP golden disagrees with captured expected rows')
 if a.native_layout:
  sys.path.insert(0,str(ROOT/'tools/s81_compile_schedule'))
  from operand_layout import cp_binding
  bound=S.Run(S.SHAPES['full']);descriptors=[]
  for epoch in range(2):
   layout=cp_binding(2,0x10002,epoch,pool=bool(epoch));db=layout['descriptor_row']+16*epoch
   bound.cp_bind(4816,4848,4880,db,0x10002,epoch,bool(epoch));descriptors.append(db)
  r=bound;result['output_base']=4880
 for name in ('in.mem','expected.mem'):(a.out/name).write_bytes((a.input/name).read_bytes())
 (a.out/'vm.mem').write_text(''.join(f'{r.vm.get(row,0):0128x}\n'for row in range(16384)))
 (a.out/'binding.json').write_text(json.dumps(dict(descriptor_rows=descriptors,output_base=result['output_base'],jobs=2,component_fixture=True,native_field_bound=False,current_rows=a.native_layout,operand_rows=[4816,4848]if a.native_layout else None),indent=2)+'\n')
 print('CP builder inputs512x2, two descriptors,32 expected rows PASS')
if __name__=='__main__':main()
