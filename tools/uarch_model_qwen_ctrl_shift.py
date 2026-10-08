"""Model-before-RTL: exact oldest-first predecoded write queue."""
from uarch_model_qwen_ctrl_head import model as head_model
import uarch_model as unified

def model():
    m=head_model()
    m['schema']='opentallas.qwen_ctrl_shift_queue.v1'
    m['source_model']='tools/uarch_model_qwen_ctrl_shift.py'
    m['change']['write_queue_onehot_bits']=4*32
    m['change']['write_queue_organisation']='Four physical oldest-first entries shift only on pop; simultaneous push targets count-pop; unchanged acceptance/issue sequence'
    m['change']['write_queue_muxes']='128 onehot shift2:1 bits plus128 insertion mux bits reserved; dynamic rp rotation removed; registered head/candidate select stored onehot before decode'
    m['area']['cell_bound_um2']+=128*unified.DFF_UM2+1024
    m['area']['frame_fit_at_55pct']=m['area']['cell_bound_um2']<m['frame_um'][0]*m['frame_um'][1]*.55
    m['area']['new_logic_reservation_basis']='1024um2 additional combinational allowance; mapped area must replace reservation'
    m['memory_ports'].append(dict(name='write_queue_onehot',depth=4,width=32,write_bytes_per_cycle=4,internal_shift_bytes_per_pop=12))
    m['replica_mux_cost']='128 PCs; +128 onehot FF/PC (16384 total), no cross-PC mux, shift occurs only on consumed write'
    m['evidence']='8be556c2e routedSS−110.94ps wq_rp1→wab_oh18; write_ready_bank→hb_oh paths to−56.40ps; no successor physical claim'
    m['runtime_state_protection']={'implemented':False,'blocks_production_adoption':True,'record':'results/rtl/qwen_ctrl_shift_20261007/runtime_protection_gate.json'}
    m['remaining'].extend(['input/reset/outputFF hold','fresh actual-corner SS/FF; no timing exception or period change'])
    return m
if __name__=='__main__':
    import json
    print(json.dumps(model(),indent=2))
