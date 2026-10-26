#!/usr/bin/env python3
"""Export the exact native RAW2341 source pins; compaction is a receiver operation."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'tools/die_plan'))
import check

def contract(plan_path,map_path):
 p=Path(plan_path);j=json.load(open(p));m=json.load(open(map_path));t=j['partition_types']['q_hub_nw'];c=next(c for c in t['hard_cores']if c['inst']=='u_hb_coll_Q_body_core');tx=next(c for c in t['contents']if c['inst']=='u_tkx_tx_Q');pins={v['name']:v for v in json.load(open(p.parent/c['pins_file']))};seen=set();raw=set();rows=[]
 for r in m['ranges']:
  for k in range(r['width']):
   source=(r['source_port'],r['source_lsb']+k);rb=r['raw_lsb']+k
   if source in seen or rb in raw:raise ValueError('projection is not a bijection')
   seen.add(source);raw.add(rb);key=f'{source[0]}[{source[1]}]';q=pins.get(key) or (pins.get(source[0])if source[1]==0 else None)
   if q is None:raise ValueError('missing actual native pin '+key)
   if check._core_face('R0',q['x'],q['y'],*c['outline_um'])!='N':raise ValueError('selected source does not face TX '+key)
   x=c['origin_um'][0]+q['x'];y=c['origin_um'][1]+q['y'];a,b=tx['origin_um'];w,h=tx['outline_um'];nearest=(min(max(x,a),a+w),min(max(y,b),b+h));rows.append(dict(raw_bit=rb,source_inst=c['inst'],source_pin=key,source_layer=q['layer'],source_xy_um=[x,y],TX_region_nearest_um=abs(x-nearest[0])+abs(y-nearest[1])))
 if raw!=set(range(2341)):raise ValueError('RAW2341 must include every bit, including all64 projected metadata bits')
 return dict(schema='opentallas.hbm.raw2341.physical_source.v1',raw_bits=2341,unique_native_pin_bits=len(seen),flit_bits=2180,preTX_dropped_bits=0,beat_bits=1171,TX_region=tx,max_pin_to_TX_region_um=max(r['TX_region_nearest_um']for r in rows),physical_gate='Bijection and source pin face only; exact native TX FF placement and timing still required',source_map_sha256=hashlib.sha256(Path(map_path).read_bytes()).hexdigest(),canonical_source_sha256=m['canonical_source_sha256'],rows=sorted(rows,key=lambda r:r['raw_bit']))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('plan');a.add_argument('--map',required=True);a.add_argument('--out',required=True);x=a.parse_args();j=contract(x.plan,x.map);Path(x.out).write_text(json.dumps(j,indent=1)+'\n');print(json.dumps({k:v for k,v in j.items()if k not in ['rows','TX_region']},indent=1))
