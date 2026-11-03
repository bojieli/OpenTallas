import json,sys,re,gzip,hashlib
from pathlib import Path
from collections import defaultdict,Counter
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/head-wave-path-query-1102/hd_st_n3_turn/geom5/geom.tsv');prep=json.loads((P/'data_only_prep.json').read_text())
masters={c[1]:(c[4]-c[2],c[5]-c[3])for c in D.cells.values()};bufs={m:dict(width_um=w,height_um=h,area_um2=w*h)for m,(w,h)in masters.items()if re.match(r'BUFx[^_]*_ASAP7',m)}
ors=[dict(master=r['root_master'],area_um2=masters[r['root_master']][0]*masters[r['root_master']][1])for r in prep['roots']];oa=sum(r['area_um2']for r in ors)
band=[18,566.46,232,580.5];ba=(band[2]-band[0])*(band[3]-band[1]);boxes=[];counts=Counter()
for c in D.cells.values():
 x0,y0,x1,y1=max(c[2],band[0]),max(c[3],band[1]),min(c[4],band[2]),min(c[5],band[3])
 if x1>x0 and y1>y0:boxes.append((x0,y0,x1,y1));counts[c[1]]+=1
# sweep exact rectangle union
xs=sorted({v for b in boxes for v in (b[0],b[2])});union=0
for a,b in zip(xs,xs[1:]):
 seg=sorted((q[1],q[3])for q in boxes if q[0]<b and q[2]>a);length=0;lo=hi=None
 for u,v in seg:
  if hi is None:lo,hi=u,v
  elif u>hi:length+=hi-lo;lo,hi=u,v
  else:hi=max(hi,v)
 if hi is not None:length+=hi-lo
 union+=(b-a)*length
# Exact selected SIMPLE library hashes for TT and FF; parse OR pin caps only.
def blocks(s,pat):
 for m in re.finditer(pat,s):
  start=s.find('{',m.start());depth=1;i=start+1
  while depth and i<len(s):
   depth+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m.group(1),s[start+1:i-1]
caps={}
for corner in ['TT','FF']:
 receipt=json.loads(Path(f'/srv/opentallas-scratch/claude/head-wave-cts-1102/input/hd_st_n3_turn/postcts_gate_{corner.lower()}.libraries.json').read_text())
 lp=Path(f'/srv/opentallas-scratch/claude/qc-l1-tail-1101/lvt_model/asap7sc7p5t_SIMPLE_RVT_{corner}_nldm_211120.lib.gz');sha=hashlib.sha256(lp.read_bytes()).hexdigest();assert any(z['sha256']==sha for z in receipt['libraries'])
 text=gzip.open(lp,'rt').read();assert re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)',text)
 cellblocks=dict(blocks(text,r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{'));rows=[]
 for r in prep['roots']:
  pins=[]
  for name,body in blocks(cellblocks[r['root_master']],r'\bpin\s*\(\s*([^\s)]+)\s*\)\s*\{'):
   if re.search(r'\bdirection\s*:\s*input\s*;',body):
    cap=re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)',body);pins.append(dict(pin=name,capacitance_ff=float(cap.group(1))if cap else None))
  rows.append(dict(original_root=r['original_root'],master=r['root_master'],pins=pins))
 caps[corner]=dict(library_sha256=sha,rows=rows,total_new_input_capacitance_ff=sum(z['capacitance_ff']for r in rows for z in r['pins']))
areas=[x['area_um2']for x in bufs.values()];amin,amax=oa+152*min(areas),oa+152*max(areas)
out=dict(scope='Conditional source-only native area/load pricing, no master selection, timing or legal placement claim; forwarded phase HOLD',new_ORs=ors,new_OR_area_um2=oa,existing_native_BUF_master_choices=bufs,new_cells=157,new_area_range_um2=[amin,amax],band=band,band_area_um2=ba,known_functional_bodies_intersecting=len(boxes),known_functional_union_area_um2=union,known_functional_occupancy_percent=union/ba*100,known_plus_new_density_percent_range=[(union+amin)/ba*100,(union+amax)/ba*100],nominal_rowheights=52,actual_rows_and_TAP_absent=True,upstream_added_input_pins=15,upstream_capacitance=caps,holds=['157 centers schematic, not row/TAP/PG-qualified','actual BUF strengths unselected; range spans only existing native noninverting BUF masters','functional bbox occupancy excludes TAP/fill/padding and is a lower bound','upstream15 loads affect counter/control analog delay; no timing benefit claimed','source/frame/proof/PG/clock/public interfaces remain held'])
(P/'area_density_pricing.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['new_OR_area_um2','new_area_range_um2','known_functional_union_area_um2','known_functional_occupancy_percent','known_plus_new_density_percent_range']}));print('cap',[(k,v['total_new_input_capacitance_ff'])for k,v in caps.items()]);print('bufs',bufs)
