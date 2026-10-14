#!/usr/bin/env python3
"""Publish final hrow source/pin/reset packet after independent real-contact replay."""
import argparse,gzip,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--candidate-dir',type=Path,required=True);a=ap.parse_args();r=a.candidate_dir.resolve()
 subprocess.run([sys.executable,str(ROOT/'tools/s81_ph/s81_ph_hrow_binding_packet.py'),'--candidate-dir',str(r)],check=True)
 d=json.load(open(r/'candidate.json'));facts=json.load(gzip.open(r/'binding_packet/closed_child_ss_ff_timing_facts.json.gz','rt'));pairs=[]
 for e in d['connectivity_edges']:
  sm=d['instances'][e['source']]['master'];dm=d['instances'][e['sink']]['master']
  for sp,dp in zip(e['source_pins'],e['sink_pins']):
   for c in ['ss','ff']:assert sp in facts[sm][c]['pins'] and dp in facts[dm][c]['pins']
   pairs.append(dict(cls=e['cls'],source=e['source']+'.'+sp,destination=e['sink']+'.'+dp,source_master=sm,destination_master=dm,source_ss_ff_pin=sp,destination_ss_ff_pin=dp,actual_rc_budget_um=None,facts_ref='closed_child_ss_ff_timing_facts.json.gz',timing_check='recovery/removal' if e['cls']=='local_reset_release' else 'setup/hold',status='Final ETM tables present; operating load/slew, actual producer clock delivery and wire RC OPEN. Raw reset exporter labels preserved.'))
 assert len(pairs)==81363
 pairfile=r/'binding_packet/all_final_etm_pairs.json.gz'
 with gzip.GzipFile(filename=str(pairfile),mode='wb',mtime=0) as f:f.write(json.dumps(pairs,separators=(',',':')).encode())
 packetpath=r/'binding_packet/packet.json';packet=json.load(open(packetpath));replay=json.load(open(r/'route_replay.json'));assert replay['actual_final_lef_pin_rebind_pass'] and replay['candidate_sha256']==ref(r/'candidate.json')['sha256']
 binding=ROOT/'results/arch/s81_vmfe_misc_2240/relay_proofs/r4_final_binding/packet.json';packet.update(status='PARTIAL PASS actual final pin geometry/capacity/replay; actual production binding and per-pair timing budgets OPEN',actual_final_master_binding=dict(**ref(binding),record_commit='32ac456ae'),all_final_etm_pair_mapping=dict(**ref(pairfile),pairs=len(pairs)),rc_budget_status='All9 final SS/FF ETMs available; actual production clock/reset producer, delivery, operating load/slew and route RC OPEN.500um is geometric ceiling only.',placement_commit='Historical88 origins/orientations5281a6feb; fresh r4 contacts/routing. No global adoption.',actual_final_pin_pair_verification=replay)
 mapped=r/'reset_classification/mapped_reset_classification.json';reset=json.load(open(mapped));packet['actual_mapped_reset_classification']=ref(mapped)
 packet['large_relay_reset_evidence']={m:dict(active_reset_endpoints=[e['instance']+'.'+e['input_pin'] for e in reset['masters'][m]['sequential_endpoints']],routed_recovery_removal=reset['masters'][m]['routed_recovery_removal'],scope='Explicit mapped RESETN recovery/removal leaf checks; actual inter-master delivery and pulse-width qualification OPEN. Exporter labels unchanged.') for m in ['dsfd_hrow_r1025','dsfd_hrow_r2079']}
 graphpath=r/'binding_packet/source_graph.json';graph=json.load(open(graphpath))
 for link in graph['local_release']:
  link['leaf_actual_recovery_removal_evidence']=ref(mapped)
  link['physical_recovery_removal_status']='Actual destination leaf SS/FF checks available and positive. Inter-master source/capture clock delivery, RN wire RC and pulse width OPEN.'
 graphpath.write_text(json.dumps(graph,indent=1)+'\n')
 packet['source_graph']=ref(graphpath)
 packetpath.write_text(json.dumps(packet,indent=1)+'\n')
 reqpath=r/'binding_packet/rc_budget_inputs_required.json';req=json.load(open(reqpath));req.update(status='OPEN actual production source delivery and operating/RC inputs; final ETMs available',missing_relay_exports=[],pending_jobs_source=None,actual_final_relay_binding=ref(binding),actual_mapped_reset_recovery_removal_evidence=ref(mapped),reset_exporter_label_policy='Raw reset ETM setup/hold labels retained. Actual mapped cell Liberty and routed reports establish recovery/removal check kind; no inferred source delivery.');reqpath.write_text(json.dumps(req,indent=1)+'\n')
 print(json.dumps({'pairs':len(pairs),'final_pin_rebind':True,'actual_pair_budget':None,'production_driver_bound':False}))
if __name__=='__main__':main()
