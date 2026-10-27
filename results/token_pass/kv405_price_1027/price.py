#!/usr/bin/env python3
"""R8-aware incremental KV405 compiler price. No RTL or final-calendar qualification."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

p=argparse.ArgumentParser()
p.add_argument('capsule_dir',type=Path)
p.add_argument('out',type=Path)
a=p.parse_args()
raw=json.loads((a.capsule_dir/'lane_cycle_delta.json').read_text())
shift=json.loads((a.capsule_dir/'shift.log').read_text())
main=json.loads((a.capsule_dir/'qwen_kvsys_r8_landing.json').read_text())
pv=json.loads((a.capsule_dir/'pv_calendar_restore_hm_r12.json').read_text())
changed={x['id']:x for x in shift['changed']}
M={x['id']:x for x in main['members']}
# PV exact calendar overrides generic R8 entries, in the same order as bind land_r8_extra.
M.update({x['id']:x for x in pv['members']})
M=list(M.values())
def age(x,old):
 return changed[x['id']]['landed'][0] if old and x['id'] in changed else x['landed']
ports={}
for vp in sorted({x['sink'] for x in M if x['sink'].startswith('vport_')}):
 values=[]
 for old in (True,False):
  gets=[x for x in M if re.fullmatch(re.escape(vp)+r'\.vq[01]_valid',x['source'])]
  rets={x['source'].split('.')[0]:age(x,old) for x in M if x['sink']==vp and re.fullmatch('in[01]_valid',x['sink_port'])}
  rt=9+max(age(x,old)+rets[x['sink']] for x in gets)
  ws={age(x,old) for x in M if x['sink']==vp and x['sink_port']=='pr_t'}
  assert len(ws)==1,(vp,ws)
  w=ws.pop()
  values.append(dict(RT=rt,W=w,total=w+rt))
 ports[vp]=dict(old=values[0],new=values[1],RT_delta=values[1]['RT']-values[0]['RT'])
assert len(ports)==16,len(ports)
maxima={k:max(x[k]['total'] for x in ports.values()) for k in ('old','new')}
for x in ports.values():
 for k in ('old','new'):x[k]['DQ_without_extra_W_pads']=maxima[k]-x[k]['total']
# Direct transport changes use grouped landed ages, not raw lane-stage sum.
rx=[x for x in shift['changed'] if x['id'].startswith(('kvs_attn.d2d__rx_payload','kvs_attn.d2d__srx','kvs_ctl.d2d__srx'))]
tx=[x for x in shift['changed'] if x['id'].startswith('d2d_kv.att_tx_')]
pvchanges=[x for x in shift['changed'] if x['table'].startswith('pv_')]
assert rx and tx and pvchanges
assert all(x['landed'][0]==x['landed'][1] for x in rx+pvchanges)
direct=max(x['landed'][1]-x['landed'][0] for x in tx)
# Same lane-class sensitivity method as toksched_1025/kv_v39r_price.py.
# Interior family serial maxima are a sensitivity, not a proven critical path.
interior=dict(vport_slg=2,pv_calendar=0,ahub_astk=1,seq_hroot=2,acal=1)
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'tools/throughput'))
import accepted_cost as AC
D=AC.load_path('qwen_rom')
base,_=AC.solve(D['nodes'],D['edges'])
def model(per_layer,embed):
 delta={x['id']:per_layer for x in D['nodes'] if re.fullmatch(r'L\d+\.attn_kv',x['id'])}
 delta['embed']=embed
 new,_=AC.solve(D['nodes'],D['edges'],delta)
 current=296341
 added=36*per_layer+embed
 return dict(accepted_cost_DAG=dict(base_cycles=base,new_cycles=new,added_cycles=new-base),
             current_QCE_additive_sensitivity=dict(base_cycles=current,added_cycles=added,new_cycles=current+added,
             clock_period_ps=833,tok_s_before=(1e12/833)/current,tok_s_after=(1e12/833)/(current+added),loss_pct=100*added/(current+added)))
result=dict(status='PENDING_CANDIDATE_INCREMENTAL_PRICE_NOT_ADOPTED',source='codex/kv-kits-1027b@b4a705f520',
 raw_lanes=len(raw['lanes']),raw_added_edge_sum=sum(x['added_cycles'] for x in raw['lanes'].values()),
 r8=dict(changed=len(shift['changed']),landed_delta_histogram=dict(Counter(x['landed'][1]-x['landed'][0] for x in shift['changed'])),
 pv_changed=len(pvchanges),pv_calendar_added_cycles=0,inbound_bundle_added_cycles=0,attention_tx_added_cycles=direct, D2D_TXDP_K_byte0_added_cycles=direct),
 vport=ports,required_fia_without_extra_W_pads={k:4+v+1 for k,v in maxima.items()},
 direct_transport_model=model(direct,0),
 serial_family_sensitivity=model(direct+sum(interior.values()),3),
 interior_family_sensitivity=interior,
 compiler_actions=[
 'Reapply authoritative R8 extras after hm_r26 composition; exact PV calendar remains fixed.',
 'Regenerate each Vport RT/DQ and PV FIRST_INPUT_AGE from final emitted bind. Raw unpadded DQ was already above15; W pads required; all RT values remain <=63.',
 'Reprice OUT attention payload+valid bundle +1/layer; incoming RX/KVN source fields stay aligned at56.',
 'Recompute EXP_START/ACAL per WN/WS (+1 AM/cal delivery), programme prg/xs/fan (+1/+1 legs), hroot_WN boot/embedding return (+1), EST embedding fan(+2). These overlap; final static compiler decides critical exposure.',
 'No ECTL Kreq/Krsp,QK_ISSUE_AGE,AHUB AP_OFS/FR_OFS,KVN_A0,or PV TRUNK_D/FLAG_D source rule leg moved in this incremental ledger.',
 'SK_TXV/SK_TXP+1 requires D2D_TXDP_K byte0+1 (other bytes unchanged); recompile one pair image and bind it on BOTH QC/KV. Final native boot image and pair calendar wait final bind; do not retain stale constants. Direct transport cost is lane-class sensitivity; final schedule can hide it in link slack. No duplicatebind/fullsim launched.'])
a.out.write_text(json.dumps(result,indent=1)+'\n')
print(json.dumps({k:result[k] for k in ('r8','required_fia_without_extra_W_pads','direct_transport_model','serial_family_sensitivity')},indent=1))
