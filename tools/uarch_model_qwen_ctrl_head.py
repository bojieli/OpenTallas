"""Model-first exact FIFO-head cut for controller source74d839a79."""
from uarch_model_qwen_ctrl_pc import model as base_model
import uarch_model as unified

def model():
    m=base_model()
    m['schema']='opentallas.qwen_ctrl_registered_head.v1'
    m['status']='CANDIDATE_NOT_ADOPTED'
    m['source_model']='tools/uarch_model_qwen_ctrl_head.py'
    m['change']={'registered_bank_eligibility_bits':32,'eligibility_logic':'lookahead open,stale,refresh-block and write-RCD masks for32banks; strict refresh and write-only queue; preserve current-cycle predicate exactly','registered_head_bits':32,'added_cycles':0,'added_token_cycles':0,
      'read_mux':'8:1 x32 FIFO read now terminates at a head register; synchronous lookahead maintains original consume cycle',
      'bypass':'empty push or simultaneous sole-head pop/push captures ingress command',
      'mechanism':'Eliminate combinational rp-to-core descriptor/write control paths; bank eligibility cut targets hb_oh feedback; boundary/reset misses remain separate blockers'}
    m['area']['cell_bound_um2']+=64*unified.DFF_UM2 + 512
    m['area']['frame_fit_at_55pct']=m['area']['cell_bound_um2']<m['frame_um'][0]*m['frame_um'][1]*.55
    m['replica_mux_cost']='one 8:1 x32 lookahead FIFO mux plus32 head FF and32 bank-eligibility FF per PC; 128 replicas; no cross-PC mux'
    m['evidence']='PC00 w18_sta_ss.log:100 violating paths launched at rp;313 at hb_oh;512um2 conservative added predicate-logic reservation; no measured timing gain yet'
    return m
if __name__=='__main__':
    import json
    print(json.dumps(model(),indent=2))
