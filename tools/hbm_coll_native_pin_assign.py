#!/usr/bin/env python3
"""Die-assigned HBM native COLL leaf pins, exact RTL headers and measured outlines.

Reads the element header manifest as input; assignments are owned by the die.
Two ASAP7 tracks per bit, M4 E/W, M5 N/S. No geometry or timing qualification
is inferred from pin assignment. Ref_tile consumes the resulting io_tcl file.
"""
import argparse,json,math,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import die_port_bind as D

def main():
 a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args()
 r=x.source.resolve();o=x.out;o.mkdir(parents=True,exist_ok=True)
 mf=r/'results/arch/hbm_p2p_1014/native_leaf_header_manifest.json';manifest=json.loads(mf.read_text())
 result=dict(schema='opentallas.hbm.coll.native.assigned_pins.v1',contract='r25gqn_v14_native_coll_candidate',owner='H-DIE',
  status='ASSIGNED_LEAF_PINS_PARENT_BIND_AND_GLOBAL_PLACEMENT_PENDING',
  rule='child clock pin receives phi minus measured child insertion; native launch/reset audit still required',
  source_header_manifest_sha256=hashlib.sha256(mf.read_bytes()).hexdigest(),leaves={},
  topk_clock_entries=39,topk_clock_map={'tile':32,'ingress':4,'selector':1,'buffer':1,'packer':1})
 for leaf in manifest['leaves']:
  spec=json.loads((r/leaf['spec']).read_text());fp=json.loads((r/leaf['kit']/'floorplan.json').read_text())
  w,h=fp['die'][2:];files=[str(r/p) for p in leaf['sources']]
  idx,_=D.rtl_index([],files,{},files);m=idx[leaf['top']];env=m.env(spec.get('params',{}))
  ports={p:(v[0],m.width(p,env)) for p,v in m.ports.items()}
  ordered=[p for ps in leaf['pins'].values() for p in ps]
  assert sorted(ordered)==sorted(ports),(leaf['top'],ordered,list(ports))
  record=dict(top=leaf['top'],params=spec.get('params',{}),outline_um=[w,h],pins={},faces={},io_tcl=leaf['name']+'_io.tcl',
   source_hashes={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in leaf['sources']})
  lines=['# H-DIE official native COLL assignment; M5 cap; two tracks per bit.']
  for face,names in leaf['pins'].items():
   bits=[(p,i,ports[p][1]) for p in names for i in range(ports[p][1])]
   length=w if face in 'NS' else h;lo=math.ceil((2.16-.012)/.048);hi=math.floor((length-2.16-.012)/.048)
   tracks=hi-lo+1;assert tracks>=2*len(bits),(leaf['top'],face,len(bits),length)
   positions=[lo+int((j+.5)*tracks/len(bits)) for j in range(len(bits))]
   assert all(b-a>=2 for a,b in zip(positions,positions[1:])),(face,'track spacing')
   for (p,i,width),t in zip(bits,positions):
    n=p if width==1 else f'{p}[{i}]';along=round(.012+t*.048,6)
    if face in 'NS':lay='M5';xy=[along,.096 if face=='S' else round(h-.096,6)];sz=[.024,.192]
    else:lay='M4';xy=[.096 if face=='W' else round(w-.096,6),along];sz=[.192,.024]
    record['pins'][n]=dict(port=p,bit=i,direction=ports[p][0],face=face,layer=lay,place_pin_xy_um=xy,pin_size_um=sz)
    lines.append(f'place_pin -pin_name {{{n}}} -layer {lay} -location {{{xy[0]:.6f} {xy[1]:.6f}}} -pin_size {{{sz[0]} {sz[1]}}} -force_to_die_boundary')
   record['faces'][face]=dict(bits=len(bits),available_tracks=tracks,min_track_spacing=min((b-a for a,b in zip(positions,positions[1:])),default=None))
  (o/record['io_tcl']).write_text('\n'.join(lines)+'\n');result['leaves'][leaf['name']]=record
 (o/'assignments.json').write_text(json.dumps(result,indent=1)+'\n')
 print(json.dumps({n:dict(top=v['top'],outline=v['outline_um'],pins=len(v['pins']),faces=v['faces']) for n,v in result['leaves'].items()},indent=1))
if __name__=='__main__':main()
