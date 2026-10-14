#!/usr/bin/env python3
"""Intake final small-relay exports without replacing historical placement evidence."""
import collections,gzip,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import child_lint,pinreg_audit
sys.path.insert(0,str(Path(__file__).resolve().parent))
import s81_ph_hrow_native_placement as P
OUT=P.OUT/'binding_packet'
COMMITS={'dsfd_die_rstsync':'626202850','dsfd_hrow_r15':'b4e5e2af3','dsfd_hrow_r23':'16f451be6'}
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def write(n,d): (OUT/n).write_text(json.dumps(d,indent=1)+'\n')
def main():
 candidate=json.load(open(P.OUT/'candidate.json'));facts={};intake={}
 for ma,commit in COMMITS.items():
  directory=ROOT/'physical/ref_tile'/(ma+'_m5')/'views'/ma
  lef=directory/(ma+'.lef');geo=child_lint.parse_lef(lef.read_text());old=json.load(open(ROOT/P.MP[ma]['evidence']))
  delta=[]
  for pin,v in geo['pins'].items():
   if pin not in old['pins']:continue
   previous=old['pins'][pin]['boxes'];now=[{'layer':r[0],'rect_um':list(r[1:])} for r in v['rects']]
   if previous!=now:delta.append({'pin':pin,'historical_cts_boxes':previous,'final_lef_boxes':now})
  ins=directory/'insertion.json';abstract=directory/'abstract.json'
  intake[ma]={'record_commit':commit,'source_commit':'06542a05c','status':'CLOSED leaf; historical parent placement not requalified','final_lef':ref(lef),'abstract':ref(abstract),'insertion':ref(ins),'insertion_corners':{c:json.load(open(ins))[c]['boundary'] for c in ['ss','tt','ff']},'outline_um':[geo['W'],geo['H']],'historical_cts_pin_evidence':ref(ROOT/P.MP[ma]['evidence']),'changed_pin_count':len(delta),'pin_deltas':delta}
  facts[ma]={c:{'liberty':ref(directory/(ma+'_'+c+'.lib')),'pins':pinreg_audit.parse_lib(directory/(ma+'_'+c+'.lib'))['pins'],'units':'ps; raw lookup tables; no assumed operating slew/load'} for c in ['ss','ff']}
 for ma,v in intake.items():
  reset='rst' if ma=='dsfd_die_rstsync' else 'rn'
  v['reset_constraint_arc_types']={c:sorted({a[0] for a in facts[ma][c]['pins'][reset]['arcs']}) for c in ['ss','ff']}
  v['async_reset_qualification']='OPEN; exported reset constraints carry setup_rising/hold_rising labels, no explicit recovery/removal types. Preserve raw labels; require validated export interpretation or explicit routed recovery/removal evidence.'
  v['raw_lookup_extrema_ps']={}
  for c in ['ss','ff']:
   values=collections.defaultdict(list)
   for n,p in facts[ma][c]['pins'].items():
    if n=='ck':continue
    for typ,related,tables in p['arcs']:
     for table in tables.values():values[typ].extend(table)
   v['raw_lookup_extrema_ps'][c]={typ:dict(min=min(xs),max=max(xs)) for typ,xs in values.items() if xs}
  v['extrema_scope']='Across all exported pin lookup entries, including load range and leaf clock boundary paths. No operating load, insertion compensation, async semantics, per-pair timing or wire budget inferred.'
 existing=json.load(gzip.open(OUT/'closed_child_ss_ff_timing_facts.json.gz','rt'));facts.update(existing)
 fp=OUT/'available_final_ss_ff_timing_facts.json.gz'
 with gzip.GzipFile(filename=str(fp),mode='wb',mtime=0) as f:f.write(json.dumps(facts,separators=(',',':')).encode())
 pairs=[];counts=collections.Counter()
 for edge in candidate['connectivity_edges']:
  sm=candidate['instances'][edge['source']]['master'];dm=candidate['instances'][edge['sink']]['master']
  for sp,dp in zip(edge['source_pins'],edge['sink_pins']):
   available=sm in facts and dm in facts
   counts['both_final_etms' if available else 'missing_large_final_etm']+=1
   if not available:continue
   p={'class':edge['cls'],'source':edge['source']+'.'+sp,'destination':edge['sink']+'.'+dp,'source_master':sm,'destination_master':dm,'source_ss_ff_pin':sp,'destination_ss_ff_pin':dp,'facts_ref':'available_final_ss_ff_timing_facts.json.gz','timing_check':'removal/recovery' if edge['cls']=='local_reset_release' else 'hold/setup','actual_rc_budget_um':None,'status':'OPEN production source clock arrivals, operating slew/load, uncertainty and routed wire RC required'}
   pairs.append(p)
 pairpath=OUT/'partial_final_etm_pairs.json.gz'
 with gzip.GzipFile(filename=str(pairpath),mode='wb',mtime=0) as f:f.write(json.dumps(pairs,separators=(',',':')).encode())
 status={'schema':'opentallas.native_hrow_final_relay_intake.v1','status':'PARTIAL final ETM evidence; no parent route/timing qualification','historical_placement_commit':'5281a6feb','historical_candidate':ref(P.OUT/'candidate.json'),'large_master_status':{m:'EARLY_FAIL_CONGESTION GRT0116; old129.6x129.6 CTS geometry historical; successor outline/pins pending' for m in ['dsfd_hrow_r1025','dsfd_hrow_r2079']},'final_small_masters':intake,'raw_timing_facts':ref(fp),'per_pair_partial_etm_mapping':ref(pairpath),'pair_counts':dict(counts),'actual_per_pair_rc_budget_status':'OPEN; actual producer clock/refclk ABI and delivery absent, large ETMs absent','immutable_price':{'relay_ff':18897,'reset_ff':54,'structural_ut_extra_edges':1,'full_unit_price':'PENDING actual parent measurement'},'source_binding_prerequisite':'Root must instantiate production TD and bind actual clock/reset producers before allocator delivery; native207 has no hrow instance'}
 write('final_relay_intake.json',status)
 packet=json.load(open(OUT/'packet.json'));packet.update(status='OPEN production source ABI; 88-instance geometry historical pending large relay successors',final_relay_intake=ref(OUT/'final_relay_intake.json'),missing_final_relay_timing_masters=['dsfd_hrow_r1025','dsfd_hrow_r2079'],rc_budget_status=status['actual_per_pair_rc_budget_status']);
 for ma,v in intake.items():packet['master_evidence'][ma].update(status='CLOSED final relay views; historical CTS pin geometry retained separately; parent delivery/timing OPEN',final_view_record_commit=v['record_commit'],final_lef=v['final_lef'],insertion=v['insertion'],insertion_corners=v['insertion_corners'],final_ss_lib=facts[ma]['ss']['liberty'],final_ff_lib=facts[ma]['ff']['liberty'])
 write('packet.json',packet)
 print(json.dumps({'pin_changes':{m:v['changed_pin_count'] for m,v in intake.items()},'pair_counts':dict(counts)}))
if __name__=='__main__':main()
