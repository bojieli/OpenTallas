#!/usr/bin/env python3
"""Independent actual LEF receiver and assigned pin-centre audit of the810 NT candidate."""
import hashlib,json,pathlib,subprocess,sys
import numpy as np
r=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(r/'tools/s81'))
import v19_pins_1014 as V
out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
rel='physical/s81_die_pins/v24_hc_norm_spread_candidate/ot_s81_hc_ctfl_nt.json'
old=json.loads(subprocess.check_output(['git','-C',str(r),'show','28dd8dbda:'+rel]))
new=json.loads((r/rel).read_text())
lef='physical/ref_tile/s81hc_ctpl_ref/views/ot_s81_hc_ctpl/ot_s81_hc_ctpl.lef'
dim,cpl=V.lef_bits(lef)
for port in old['ports']:
 if port not in ['fdx_local','fv_local']:assert old['ports'][port]==new['ports'][port],port
legs=[];moved=[];internal={}
for port,src in [('fdx_local','fdx'),('fv_local','fv')]:
 for b,(before,after) in enumerate(zip(old['ports'][port]['per_bit'],new['ports'][port]['per_bit'])):
  if before!=after:moved.append(dict(port=port,bit=b,old_x=before[2],new_x=after[2],move_um=round(abs(after[2]-before[2]),3)))
  sy=810-412.56-25.92+.042;pin=cpl[src][b]
  for g in range(4):
   for h,YPL in enumerate([211.68,464.4]):
    x=144.72*g+pin[2];y=810-YPL-dim[1]+pin[3]
    legs.append(dict(source_port=port,source_bit=b,receiver_column=g,receiver_half=h,receiver_port=src,receiver_bit=b,old_distance_um=round(abs(before[2]-x)+abs(sy-y),3),new_distance_um=round(abs(after[2]-x)+abs(sy-y),3)))
assert max(t['new_distance_um'] for t in legs)<=499.8
for label,rec in [('old_v24',old),('current810',new)]:
 pairs=[]
 for a,b in [('fdx','fdx_local'),('fv','fv_local')]:pairs.extend(zip([x[2] for x in rec['ports'][a]['per_bit']],[x[2] for x in rec['ports'][b]['per_bit']]))
 lo=np.array([min(a,b) for a,b in pairs]);hi=np.array([max(a,b) for a,b in pairs])
 internal[label]=dict(max_cut_bits=max(int(((lo<x)&(hi>x)).sum()) for x in np.arange(.5,576.72,.5)),lateral_sum_um=round(float((hi-lo).sum()),3),max_lateral_um=round(float((hi-lo).max()),3))
(out/'ctfl_810_all_receiver_legs.json').write_text(json.dumps(legs,indent=1)+'\n')
rep=json.loads((r/'physical/s81_die_pins/v24_hc_norm_spread_candidate/report.json').read_text())
summary=dict(scope='Candidate CTflS pin correction at S-DIE delegated810 NT rows. Only CTflS changes; clocks and other masters byteidentical. Firstcrootr/lastchain anchors and whole-slab adoption open.',old_pin_commit='28dd8dbda',cth_candidate_um=[576.72,810.0],ctfl_origin_from_north_um=412.56,ctpl_receivers=[dict(column=g,half=h,origin_from_north_um=[round(144.72*g,3),y],outline_um=dim) for g in range(4) for h,y in enumerate([211.68,464.4])],all_actual_directed_legs=len(legs),old_over500=sum(t['old_distance_um']>500 for t in legs),old_max_um=max(t['old_distance_um'] for t in legs),new_over500=sum(t['new_distance_um']>500 for t in legs),new_max_um=max(t['new_distance_um'] for t in legs),changed_bits=moved,internal=internal,direct_chain_seams=rep['seams_max_um'],gate_requalification='OldCTflgate belongs tooldpins and is invalid fornewpinbytes. Freshsource-boundphysicalmeasurement required; functional RTL remains byteidentical to28dd proof.',sha256={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in [rel,rel.replace('.json','.tcl'),lef,'tools/s81/hc_norm_straight_pins.py']})
(out/'ctfl_810_repin_audit.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k in ['all_actual_directed_legs','old_over500','old_max_um','new_over500','new_max_um','internal']}))
