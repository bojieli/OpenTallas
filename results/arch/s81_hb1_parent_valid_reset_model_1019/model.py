"""Bounded recurrence and immutable Liberty arithmetic; no RTL engine or physical proof."""
from pathlib import Path
import hashlib,itertools,json,re
P=Path(__file__).resolve().parent
L=Path('/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM')
masters=['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R']
libs={}; prices={}
for corner in ['TT','FF']:
 p=L/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib';t=p.read_text();libs[corner]=hashlib.sha256(p.read_bytes()).hexdigest();prices[corner]={}
 for m in masters:
  c=t[t.index('cell ('+m+')'):];c=c[:c.find('\n  cell (',1)];d={'area_um2':float(re.search(r'area\s*:\s*([0-9.]+)',c)[1])}
  for pin in ['CLK','RESETN','SETN']:
   if 'pin ('+pin+')' not in c:continue
   s=c[c.index('pin ('+pin+')'):];s=s[:s.index('}')];d[pin+'_fF']=float(re.search(r'capacitance\s*:\s*([0-9.]+)',s)[1])
  prices[corner][m]=d
# q[j] is state just before an edge. A low pulse asynchronously clears selected stages.
# Consumer samples pre-edge q[3]. Release edges E0,E1,E2 keep consumer reset; E3 firstuse.
def trace(initial,reset_stages,relay_edges,consumer_first=3):
 q=list(initial)
 for j in reset_stages:q[j]=0
 events=[]
 for e in range(5):
  events.append({'edge':e,'pre_q':q[:],'consumer_eligible':e>=consumer_first,'stale_eligible':bool(e>=consumer_first and q[3])})
  if e in relay_edges:q=[0]+q[:-1] # source-invalid prefix ONLY; source publication separately constrained
 return events
cases=[]
for mask in range(16):
 stages=[j for j in range(4) if mask>>j&1]
 ok=all(not any(r['stale_eligible'] for r in trace(s,stages,set(range(5)))) for s in itertools.product([0,1],repeat=4))
 cases.append({'reset_stages':stages,'same_root_calendar_no_stale_firstuse':ok})
assert all(c['same_root_calendar_no_stale_firstuse']==(0 in c['reset_stages']) for c in cases)
# Adversarial permitted independent calendar: VP releases while downlink stopped.
# Restart at E3 exposes stale q3 immediately unless q3 reset, and then stale q2/q1 later.
independent=[]
for mask in range(16):
 stages=[j for j in range(4) if mask>>j&1]
 ok=all(not any(r['stale_eligible'] for r in trace(s,stages,{3,4})) for s in itertools.product([0,1],repeat=4))
 # Examine enough restart edges to expose all four stages.
 for s in itertools.product([0,1],repeat=4):
  q=list(s)
  for j in stages:q[j]=0
  for e in range(4):
   ok=ok and not q[3];q=[0]+q[:-1]
 independent.append({'reset_stages':stages,'stopped_relay_then_restart_no_old_valid':bool(ok)})
assert sum(c['stopped_relay_then_restart_no_old_valid'] for c in independent)==1
assert independent[-1]['stopped_relay_then_restart_no_old_valid']
# Every arbitrary state, every between-edge reset/reassert: all stages cleared immediately;
# payload is intentionally unspecified and has no arithmetic/latency changes.
zero_pulse_witness=trace([1,1,1,1],[],set(range(5)))
stopped_stage0_witness=trace([1,1,1,1],[0],{3,4})
variants=[]
for name,n in [('sw_stage0_phase_conditional',5),('six_authority_stage0_phase_conditional',30),('sw_all_stages_local_only',20),('six_authority_all_stages',120)]:
 v={'name':name,'converted_existing_ff':n,'added_state_bits':0,'added_payload_ff':0,'data_edge_delta':0,'liberty_arithmetic':{}}
 for c,p in prices.items():
  a,b=(p[m] for m in masters)
  v['liberty_arithmetic'][c]={'area_delta_um2':n*(b['area_um2']-a['area_um2']),'clock_cap_delta_fF':n*(b['CLK_fF']-a['CLK_fF']),'new_RESETN_load_fF':n*b['RESETN_fF'],'new_SETN_tie_load_fF':n*b['SETN_fF']}
 variants.append(v)
source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((P/'source').iterdir())}
assert source['ot_s81sl_xr.sv']=='cc31c2d1607af9e0ac41357d3afaf19e6665b4f94ce4911e2dcaf078ec1167c3'
out={'scope':'STRUCTURAL MODEL ONLY: no RTL execution, reachability, mapped-parent or phase qualification','source_commit':'ceaed19c4','private_receipt_base':'edd84d4c3','source_sha256':source,'library_sha256':libs,'actual_library_masters':prices,'downlink':{'DL':4,'leaves':5,'width':594,'valid_bit_offsets_lsb':{'g_v':34,'rb_v':67,'cw_v[0]':156,'cw_v[1]':157,'sw_v':432,'c_v':593},'authority_bits_per_stage':6,'existing_authority_ff':120,'payload_other_unreset_ff':11760},'same_root_exhaustive_16_initial_states_x16_reset_masks':cases,'stopped_relay_exhaustive_16_initial_states_x16_reset_masks':independent,'zero_clock_pulse_no_repair_witness':zero_pulse_witness,'stage0_stopped_clock_counterexample':stopped_stage0_witness,'variants':variants,'whole_parent_clock_phase_binding':None,'actual_root_pulse_authority':None,'selected_parent_native_master_census':None,'physical_reset_distribution_and_ties':None,'all841_extra_copy_firstuse_proof':False}
(P/'model.json').write_text(json.dumps(out,indent=2)+'\n')
print('MODEL recurrence PASS: 16 initial states x16 reset masks, same-root and independently stopped relay; causal omitted-stage failures retained. NOT RTL/production reachability.')
print(json.dumps(variants,indent=2))
