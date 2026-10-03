#!/usr/bin/env python3
"""Frozen PC40 bare-ACK binding review; no compile, no system proof."""
import pathlib,json,hashlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
REC=pathlib.Path('results/uarch/Euclid_W4_RFACK_identity_contract_20261003/PC40-bare-ACK-review-r8')
def review():
 p=ROOT/REC
 for name,want in json.loads((p/'artifact-pins.json').read_text()).items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=want:raise ValueError('artifact pin '+name)
 for name,pin in json.loads((p/'source-pins.json').read_text()).items():
  if hashlib.sha256((p/name).read_bytes()).hexdigest()!=pin['sha256']:raise ValueError('peer snapshot pin '+name)
 bridge=(p/'bridge.sv').read_text();rf=(p/'RF-bare.sv').read_text();tb=(p/'tb.sv').read_text();consumer=(p/'consumer.sv').read_text()
 for fragment in ['.host_ack_identity(identity)','input wire local_ack_valid,output wire local_ack_ready','!local_ack_valid && !remote_ack_valid && !local_rsp_valid']:
  if fragment not in bridge:raise ValueError('bare controller source changed')
 for fragment in ['wire idle = rst_n && !read_pending && !rsp_valid && !ack_valid','if(write_go) begin ack_valid<=1','else if(ack_valid && ack_ready) ack_valid<=0']:
  if fragment not in rf:raise ValueError('causal primitive premise changed')
 header=rf[:rf.index(');')]
 if 'ack_owner' in header or 'ack_slot' in header:raise ValueError('RF is not bare-ACK source')
 selector=re.search(r'assign local_wr_addr=(.*?);',bridge).group(1)
 branches=re.findall(r"phase==(\w+)\?9'd(\d+)",selector);fallback=int(re.search(r":9'd(\d+)$",selector).group(1))
 if dict(branches)!={'A_WR':'17','B_WR':'18','OUT_WR':'17','CONST_WR':'18'} or fallback!=19:raise ValueError('address selector no longer matches reviewed premise')
 ackslots={'A_ACK':17,'B_ACK':18,'OUT_ACK':17,'CONST_ACK':18,'FMAX_ACK':19}
 for phase in ackslots:
  if phase in dict(branches):raise ValueError('ACK phase is in selector; re-review necessary')
 if 'force' in tb or 'release' in tb:raise ValueError('negative stimuli changed; re-review scope')
 if len(re.findall(r'\brst_n\s*=\s*0\s*;',tb))!=1:raise ValueError('reset stimulus differs reviewed startup-only snapshot')
 if 'assign rd_a=9\'d19' not in consumer or 'OUTPUT_VALUE:if(result_ready)next_raw[2:0]=ACK' not in consumer:raise ValueError('actual consumer changed')
 r=json.loads((p/'review-r8.json').read_text())
 if r['expected_ACK_slots']!=ackslots or r['model_before_repair']['W4_full_gate_terminal'] or not r['no_build_or_RTL_change']:raise ValueError('scope promotion')
 return {'status':'PASS_FROZEN_SOURCE_AUDIT_ONLY','actual_ACK_phase_address_selector':fallback,'required_expected_slots':ackslots,'bare_retag_negative_qualification':False,'W4_terminal':False,'source_or_job_changed':False,'compiled_or_solver':False}
if __name__=='__main__':print(json.dumps(review(),indent=2,sort_keys=True))
