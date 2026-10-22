"""Encode component-only dated rows after authentic VM input preload.

These controlled bench dates are not token producer dates. Input index values
and expected outputs in cases.mem are deliberately excluded from descriptors.
"""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hbm_layer_vehicle.su_indexed_gather_2000 import encode_programme_row,phases

def main():
 cases,output=map(Path,sys.argv[1:3]);r,w=map(int,sys.argv[3:5])
 profile=phases(r,w);gap=profile['done']+2
 layouts=json.loads(Path(sys.argv[5]).read_text()) if len(sys.argv)>5 else None
 raw=[int(x,16)for x in cases.read_text().split()]
 if len(raw)!=18:raise ValueError('actual six records from each of three layers required')
 output.mkdir(parents=True,exist_ok=True)
 for layer,start in (('L0',0),('L2',6),('L14',12)):
  rows=[]
  for i,value in enumerate(raw[start:start+6]):
   desc=dict(index_word=(value>>136)&0xffffff,score_base=(value>>112)&0xffffff,
             score_limit=(value>>88)&0xffffff,dest_word=(value>>64)&0xffffff,dyn_mul=1)
   if layouts:
    layout=layouts[layer];desc.update(index_word=layout['index_base']+i,score_base=layout['segment_bases'][0],
                                     score_limit=max(layout['segment_bases'])+96,segment_bases=layout['segment_bases'])
   rows.append(encode_programme_row(desc,start=8+gap*i,release=8+gap*(i+1),row_identity=i))
  (output/(layer+'_6rows.mem')).write_text('\n'.join(f'{row:064x}'for row in rows)+'\n')
 (output/'scope.json').write_text(json.dumps(dict(scope='MINIMUM COMPONENT after true input preload; not production token dates',
  read_sample=r,write_commit=w,release_gap=gap,segmented96=layouts is not None,source_layouts=layouts,cases_sha256=hashlib.sha256(cases.read_bytes()).hexdigest(),
  encoder_sha256=hashlib.sha256(Path(__file__).with_name('su_indexed_gather_2000.py').read_bytes()).hexdigest()),indent=2)+'\n')
 print('ENCODED three actual six-row component programmes; runtime index and expected O excluded from commands')
if __name__=='__main__':main()
