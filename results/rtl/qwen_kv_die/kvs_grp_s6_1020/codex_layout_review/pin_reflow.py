import json,re,math,hashlib,sys
from pathlib import Path
wt=Path(__file__).resolve().parents[5];r=Path(__file__).resolve().parent;previews=Path(sys.argv[1])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def natural(s):return [int(v) if v.isdigit() else v for v in re.split(r'(\d+)',s)]
def base(s):return re.sub(r'\[\d+\]$','',s)
def point(wanted):
 dbu=math.floor(wanted*1000+.5)
 return (12+48*math.floor((dbu-12)/48+.5))/1000
for kit in ['qkd_kvs_grp_s6a','qkd_kvs_grp_h_s6a']:
 sp=wt/'physical/ref_tile'/kit/'spec.json';spec=json.loads(sp.read_text());dp=previews/kit/'gate_layout_floorplan.json';dump=json.loads(dp.read_text());ports=[p for p in dump['pins'] if p[0] not in ('VDD','VSS')];groups={};matched=set();bad=[]
 for face,bases in spec['pins'].items():
  for bs in bases:
   ps=sorted([p for p in ports if base(p[0])==bs],key=lambda p:natural(p[0]));assert ps,(kit,bs);lo,hi=spec['pin_ranges'][bs];groups[bs]=(face,ps)
   for i,p in enumerate(ps):
    assert p[0] not in matched;matched.add(p[0]);wanted=lo+(hi-lo)*(i+.5)/len(ps);pred=point(wanted);actual=(p[3]+p[5])/2 if face in 'WE' else (p[2]+p[4])/2
    if abs(actual-pred)>1e-7:bad.append([p[0],actual,pred])
 assert len(matched)==len(ports) and not bad,(kit,len(ports),len(matched),bad[:5])
 for h in [432.0,475.2]:
  ranges={bs:([round(2.5+(v-2.5)*(h-5)/(388.8-5),3) for v in pair] if groups[bs][0] in 'WE' else pair) for bs,pair in spec['pin_ranges'].items()};new=[]
  for bs,(face,ps) in groups.items():
   lo,hi=ranges[bs]
   for i,p in enumerate(ps):
    wanted=lo+(hi-lo)*(i+.5)/len(ps);pos=point(wanted);name,layer,x0,y0,x1,y1=p;old=[(x0+x1)/2,(y0+y1)/2];parallel=old[1] if face in 'WE' else old[0];delta=pos-parallel
    if face in 'WE':x0,x1=(0,x1-x0) if face=='W' else (388.8-(x1-x0),388.8);y0+=delta;y1+=delta
    else:x0+=delta;x1+=delta;y0,y1=(0,y1-y0) if face=='S' else (h-(y1-y0),h)
    new.append(dict(port=name,face=face,layer=layer,old_pin_center_um=old,new_pin_center_um=[round((x0+x1)/2,6),round((y0+y1)/2,6)],new_bbox_um=[round(v,6) for v in (x0,y0,x1,y1)],requested_alongface_um=wanted))
  tag=kit+'_'+str(h).replace('.','p');payload=dict(scope='PROSPECTIVE SOURCE-PIN MODEL, not a placement/gate result. Actual canonical balanced place_pin math with explicit1nm-authored scaled W/Epin_ranges; DBU1nm then nearest12mod48nm track tieup exactly reproduces ALL original pins. Candidate source spec must retain these literal ranges/portorder/one-layer settings. No standard-cell freedom, clock/reset or parent-age qualification implied.',baseline_pin_count=len(ports),baseline_reconstruction_mismatches=len(bad),actual_baseline_dump_sha256=sha(dp),original_spec_sha256=sha(sp),generator_sources={str(p.relative_to(wt)):sha(p) for p in [wt/'tools/ref_tile/ref_tile.py',wt/'tools/run_abi3_physical.py']},outline_um=[388.8,h],pin_ranges=ranges,pins=spec['pins'],declared_clock_ports=['ck','hck'],declared_reset_ports=spec['reset_ports'],group_max=1,h_layer='M4',v_layer='M5',dbu_per_um=1000,track_alongface_um=dict(offset=.012,pitch=.048),ports=new)
  (r/(tag+'_pin_model.json')).write_text(json.dumps(payload,indent=1)+'\n');print(kit,h,'baseline',len(ports),'mismatch',len(bad))
