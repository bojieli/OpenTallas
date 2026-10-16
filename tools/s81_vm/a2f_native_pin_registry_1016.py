#!/usr/bin/env python3
"""Bind exact actual native/gate pin shapes to every source-current hard leaf.
This records geometry provenance and missing ABI bits; never substitutes centres
or infers native qualification from LEF presence. Run on a pinned input bundle.
"""
import argparse,collections,gzip,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hier_contract'))
import child_lint as CL

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 bindings=json.loads((a.inputs/'bindings.json').read_text());models={};leaves=[];missing=[]
 for leaf in bindings['leaves']:
  key=leaf['pin_source']
  if key not in models:
   p=a.inputs/key;assert hashlib.sha256(p.read_bytes()).hexdigest()==leaf['sha256'],str(p)
   if leaf['pin_kind']=='lef':
    m=CL.parse_lef(p.read_text());W,H=m['W'],m['H'];pins={n.replace('\\',''):v['rects']for n,v in m['pins'].items()if not CL.is_pg(n,v)};cell=m['name']
   else:
    m=json.loads(p.read_text());x,y,xx,yy=m['die'];assert x==y==0;W,H=xx,yy;cell=m['top'];pins=collections.defaultdict(list)
    for n,layer,x,y,xx,yy in m['pins']:
     if n not in ('VDD','VSS'):pins[n.replace('\\','')].append([layer,x,y,xx,yy])
   ports={}
   for n,rects in pins.items():
    choices=[(CL.face_of(r,W,H),r)for r in rects];faces=sorted({f for f,r in choices if f});r=next((r for f,r in choices if f),rects[0]);ports[n]=dict(rects=rects,faces=faces,anchor_um=[(r[1]+r[3])/2,(r[2]+r[4])/2],anchor_layer=r[0],anchor_face=next((f for f,r in choices if f),None))
   models[key]=dict(physical_cell=cell,outline_um=[W,H],source_sha256=leaf['sha256'],pin_kind=leaf['pin_kind'],pin_source_original=leaf['pin_source_original'],pins=ports)
  mod=models[key];absent=[]
  for p,v in leaf['ports'].items():
   for b in range(v['bits']):
    n=p+'['+str(b)+']'if v['bits']>1 else p
    if n not in mod['pins']and not(v['bits']==1 and p+'[0]'in mod['pins']):absent.append(n)
  row={**leaf,'physical_cell':mod['physical_cell'],'outline_um':mod['outline_um'],'missing_bits':absent};leaves.append(row)
  if absent:missing.append(dict(path=leaf['path'],master=leaf['master'],kit=leaf['kit'],missing_bits=absent))
 with gzip.open(a.out/'models.json.gz','wt')as f:json.dump(models,f,separators=(',',':'))
 (a.out/'leaves.json').write_text(json.dumps(dict(leaves=leaves),indent=1)+'\n')
 summary=dict(schema='opentallas.s81.actual-native-pin-registry.v1',scope='Exact actual pin shapes and macro outlines only; source/parameter/native/die qualification remains separately required. No synthesized centres.',leaf_instances=len(leaves),unique_pin_models=len(models),signal_pin_shapes=sum(sum(len(p['rects'])for p in m['pins'].values())for m in models.values()),leaf_instances_missing_bits=len(missing),missing_bits=missing,physical_signal_layers=dict(collections.Counter(r[0]for m in models.values()for p in m['pins'].values()for r in p['rects'])),interior_signal_ports=sum(not p['faces']for m in models.values()for p in m['pins'].values()),binding_manifest_sha256=hashlib.sha256((a.inputs/'bindings.json').read_bytes()).hexdigest())
 (a.out/'summary.json').write_text(json.dumps(summary,indent=1)+'\n');print(json.dumps(summary,indent=1));return int(bool(missing))
if __name__=='__main__':sys.exit(main())
