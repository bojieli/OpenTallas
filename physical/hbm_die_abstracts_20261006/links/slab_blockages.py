#!/usr/bin/env python3
"""Convert source-pinned reservation rectangles to placement blockages.
No slab LEF, Liberty, RTL instance, invented pins or timing/protection claim.
"""
import argparse,hashlib,json,re
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--def',dest='deffile',type=Path,required=True)
 p.add_argument('--abstract-list',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 raw=a.deffile.read_text();scale=int(re.search(r'UNITS DISTANCE MICRONS (\d+)',raw)[1])
 fam={f['family']:f for f in json.loads(a.abstract_list.read_text())['families']}
 rows=[]
 for name,master,x,y,ori in re.findall(r'-\s+(\S+)\s+(hfd_(?:host|serdes)_slab)\s+\+ FIXED \( (\d+) (\d+) \) (\S+) ;',raw):
  f=fam[master]
  if f['ports']:raise ValueError('reservation acquired real pins: explicit owner contract required')
  if len(f['size_um'])!=1 or ori!='N':raise ValueError('ambiguous/rotated slab rectangle')
  w,h=f['size_um'][0];x=int(x)/scale;y=int(y)/scale
  rows.append(dict(name=name,master=master,rectangle_um=[x,y,x+w,y+h],pins=[],logic=False))
 if len(rows)!=3:raise ValueError('expected two SerDes + one host reservation')
 a.out.mkdir(parents=True,exist_ok=False)
 (a.out/'reservation_blockages.tcl').write_text('# Explicit reservation blockages; no logic macros.\n# Reference r14b geometry only; corrected parent allocation required before adoption.\n'+''.join('create_blockage -region {'+' '.join(f'{v:.6f}' for v in r['rectangle_um'])+'}\n' for r in rows))
 (a.out/'outlines.json').write_text(json.dumps(dict(schema='opentallas.hbm.links.slab_blockages.v1',def_sha256=sha(a.deffile),abstract_list_sha256=sha(a.abstract_list),outlines=rows,parent_adopted=False,geometry_status='REFERENCE_ONLY_PARENT_INVALIDATED'),indent=2)+'\n')
 print('3 explicit blockages; zero logic masters; zero invented pins')
if __name__=='__main__':main()
