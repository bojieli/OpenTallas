#!/usr/bin/env python3
"""Source-bound tail-edge derivation, not a provider or simulator measurement."""
import json,hashlib,subprocess,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
CORE='rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv'
QE='rtl/hdc/v41/ot_hdc_v41_qe.sv'
def source(path):return subprocess.check_output(['git','show',PIN+':'+path],cwd=ROOT).decode()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def derive():
 q=source(QE);c=source(CORE)
 snippets={QE:["wire pend = (rd_n != got_n) || x_v || w_we[0];", "S_DRAIN: if ((mode == LINQ) ? (oc == otot && !w_we[0]) : !pend) st <= S_IDLE;", "else idle <= (st == S_IDLE) && !accept && !(|w_we);", "kvb_v <= aq_vo && mode == QDQ8", "w_we[wp] <= (mode == LINQ)", "if (st == S_LOAD && got_ev) got_n <= got_n + 1'b1;"],
 CORE:[".xr_re(wqr_re), .xr_addr(wqr_addr), .xr_q(wqr_q)","wire [4:0] idles = {he_idle, xu_idle, qe_idle, su_idle, me_idle};", "wire waited = ((d_wait & ~(idles & ~gos)) == 5'd0);", "su_go <= (d_unit == 3'd2);", "S_GO: begin pc <= pc + 1'b1; st <= S_FETCH; end"]}
 for p,parts in snippets.items():
  text=q if p==QE else c
  for part in parts:
   if part not in text:raise ValueError('source semantics not bound: '+part)
 # Calendar premise pinned before measurement: QEaccept7, terminal/VM samples24..39.
 # A terminal sampled at E was registered from AQ valid at E-1. Therefore final
 # aq_vo contributes got_n and registered w_we at38; x_v already clear after25.
 state='LOAD';idle=0;w_we=1;got_n=16;rd_n=16;x_v=0;su_go=0;tail=[]
 for edge in range(39,44):
  pre=dict(state=state,idle=idle,w_we=w_we,got_n=got_n,rd_n=rd_n,x_v=x_v,su_go=su_go)
  pend=rd_n!=got_n or x_v!=0 or w_we!=0
  ready=(state=='IDLE')
  waited=bool(idle) # PC21 wait4 selects QE; all other engines irrelevant.
  physical_su=bool(su_go) # matching FULL producer and actual SU ready at this edge.
  next_state='DRAIN' if state=='LOAD' and got_n==16 else ('IDLE' if state=='DRAIN' and not pend else state)
  next_idle=int(state=='IDLE' and w_we==0)
  next_go=int(edge>=39 and waited and not physical_su)
  tail.append(dict(edge=edge,pre=pre,pend=bool(pend),wait4_QE_idle=waited,
    physical_SU_accept=physical_su,post=dict(state=next_state,idle=next_idle,w_we=0,su_go=next_go)))
  state,idle,w_we,su_go=next_state,next_idle,0,next_go
 accepts=[e['edge'] for e in tail if e['physical_SU_accept']]
 if accepts!=[43]:raise AssertionError('source edge derivation')
 return {'status':'SOURCE_EDGE_DERIVATION_NOT_RUNTIME_MEASUREMENT','source_commit':PIN,
  'source_sha256':{QE:sha(q),CORE:sha(c)},'source_requirements':snippets,
  'premise':{'real_start':0,'QE_accept':7,'registered_terminal_VM_preedge_samples':list(range(24,40)),
   'last_AQ_valid_preedge':38,'got_n16_postedge':38,'last_xr_request_registered_postedge':23,'last_x_v_asserted_postedge':24,'x_v_clear_postedge':25,
   'basis':'Pinned prior actual-QE calendar and unchanged AQ/kvb/w_we registration; no new measured input or fitted latency.'},
  'tail':tail,'conclusion':{'QE_state_IDLE_postedge':40,'QE_idle_high_postedge':41,'QE_idle_first_preedge_sample':42,
    'PC21_SU_go_registered_postedge':42,'physical_SU_accept_preedge':43,
    'cancelled_producer_ACK_registered_postedge':42,'local_ACK_first_preedge_sample':43},
  'old44':'Rejected: counted a further edge after idle already became visible to waiting S_ISSUE at42. No overlay register stage added.',
  'healthy_matching_producer':'Full after capture sample39; no issue-ready diagnostic feedback into stop. SU ready, no fault, PC21 already waits in S_ISSUE.',
  'physical_provider':False,'runtime_measurement':False}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
 result=derive();p=Path(a.out)
 with p.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result['conclusion']))
