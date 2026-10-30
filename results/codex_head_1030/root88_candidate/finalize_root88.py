#!/usr/bin/env python3
import copy,json,re,shutil,sys
from pathlib import Path
root,src,out=map(Path,sys.argv[1:4]);sys.path[:0]=[str(root/'tools/die_plan'),str(root/'tools/s81_head')]
import schema as S,reset_tree as RT,gen_rtl as G,clock_landings as C,landing_contract as LC
from head_start_reset_aliases import patch_rtl
from head_start_sources import complete_top
raw=json.loads((src/'source_plan.json').read_text());side=json.loads((src/'source_sidecar.json').read_text());st=json.loads((src/'start_stages_src25q.json').read_text())
assert not out.exists();out.mkdir()
for p in src.iterdir():
 if p.is_dir():shutil.copytree(p,out/p.name)
side['count_aligned']['root_settle_cycles']=88
st['root_settle']=88
for s in st['stages']:
 if s['root']:assert s['settle']==74;s['settle']=88
st['root_settle_guard']=dict(raw_relative_span=84,guard_cycles=4,prototype_minimum=88,added_boot_cycles=24,delta_from_previous_boot_cycles=14,previous_settle_cycles=74,baseline_settle_cycles=64,added_steady_cycles=0)
txt=(src/'start_stages.sv').read_text();txt,n=re.subn(r'ot_dp_landing_root #\(\.SETTLE\(74\)\)', 'ot_dp_landing_root #(.SETTLE(88))',txt);assert n==1
(out/'start_stages.sv').write_text(txt)
# Measured native eight-column experiment: only the existing tile writer band's W margin changes.
ci=side['collector']['types']['hd_tile'];ci['bands']['i']['rect_um'][0]=12.96
for s in ci['local_sources']:
 if s.get('band',{}).get('rect_um')==[17.28,708.48,47.52,1008.512]:s['band']['rect_um'][0]=12.96
# A fresh plan, with no builder memoization, is the sole authority for source coordinates.
pp=out/'source_plan.json';pp.write_text(json.dumps(raw,indent=1)+'\n');P=S.Plan(raw,pp);trees={};changes=[]
for tn,t in P.types.items():
 rows=t.get('reset_start_raw_exports',[])
 if not rows:continue
 T=RT.for_type(P,tn);rr=RT.start_relays(T) if T.get('start') else T['relays'];by={r['name']:r for r in rr};trees[tn]=(T,by)
 for row in rows:
  r=by[row['instance']];assert r['q']==row['net'] and r['depth']==row.get('depth',r['depth']) and r.get('role') in ('raw','boot','bootstrap_transport'),(tn,row,r)
  d=max(abs(a-b) for a,b in zip(row['xy_um'],r['xy']));assert d<.05,(tn,row,d)
  if d>1e-9:changes.append(dict(type=tn,port=row['port'],old=row['xy_um'],actual=r['xy'],max_delta_um=d))
  row['xy_um']=list(r['xy'])
print('CANONICAL_RAW',len(changes),max((r['max_delta_um'] for r in changes),default=0),flush=True)
# Import the narrow PG-safe/deduplicated physical pin allocator, retaining exact source records.
from allocate_raw_pin_sites import allocate
pinchanges=allocate(raw,st,S,LC)
pp.write_text(json.dumps(raw,indent=1)+'\n');P=S.Plan(raw,pp);off=RT.wf_plan(P);hops=[];releases={}
for sg in st['stages']:
 rs=sg.get('reset_source')
 if not rs:continue
 T,by=trees[rs['type']];row=next(r for r in raw['partition_types'][rs['type']]['reset_start_raw_exports'] if r['port']==rs['port']);r=by[row['instance']]
 release=off['parts'][rs['part']]['release']-RT.release_clocks(T)+RT.entry_stages(T)+r['depth']
 assert release==rs['raw_release'],(sg['id'],'producer depth/release changed',rs['raw_release'],release)
 xy=P.to_die(rs['part'],r['xy']);rs.update(instance=r['name'],net=r['q'],xy_um=list(xy),local_xy_um=list(r['xy']),raw_release=off['parts'][rs['part']]['release']-RT.release_clocks(T)+RT.entry_stages(T)+r['depth'])
 sg['reset_hop_um']=round(sum(abs(a-b) for a,b in zip(sg['clock_pin_xy_um'],xy)),6);hops.append(sg['reset_hop_um']);releases[sg['id']]=rs['raw_release']
 if sg['reset_port'] in st.get('reset_ports',{}):st['reset_ports'][sg['reset_port']].update(rs)
rid=next(s['id'] for s in st['stages'] if s['root']);span=max(v-releases[rid] for v in releases.values());assert span==84 and max(hops)<=405,(span,max(hops))
(out/'start_stages_src25q.json').write_text(json.dumps(st,indent=1)+'\n');(out/'source_sidecar.json').write_text(json.dumps(side,indent=1)+'\n')
L=C.Landings(raw,side);ep=G.bus_epochs(P)
(out/'ot_dp_cells.sv').write_text(G.CELLS)
for tn,t in sorted(P.types.items()):
 if t.get('hard'):continue
 (out/(t['module']+'.sv')).write_text(patch_rtl(L.type_rtl(tn,G.wrapper(P,tn,ep)),t.get('reset_start_raw_exports',[])))
 print('RTL',tn,flush=True)
top,spares=complete_top(L.top_rtl(G.die_top(P,ep),{tn:t['module'] for tn,t in P.types.items()}),raw,st);(out/(G.sv_id(P.name)+'_top.sv')).write_text(top)
report=dict(root_settle_cycles=88,raw_relative_span=span,guard_cycles=4,delta_boot_cycles=14,added_steady_cycles=0,max_reset_hop_um=max(hops),raw_coordinate_changes=changes,pin_site_changes=pinchanges,raw_release_absolute_min=min(releases.values()),raw_release_absolute_max=max(releases.values()),all_part_raw_release_max=max(p['release'] for p in off['parts'].values()),unused_uniform_exports=len(spares))
(out/'root88_report.json').write_text(json.dumps(report,indent=1)+'\n');shutil.copy(src/'report.json',out/'report.json');print('ROOT88_SOURCE_PASS',json.dumps({k:v for k,v in report.items() if k not in ('raw_coordinate_changes','pin_site_changes')}),flush=True)
