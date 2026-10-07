"""Model before RTL: typed cancellation of aborted but physically unissued WR."""
def qwen_ctrl_write_cancel_model():
 from uarch_model_qwen_ctrl_write_ledger import qwen_ctrl_write_ledger_model
 m=qwen_ctrl_write_ledger_model()
 m.update(status='SIZED_NOT_PHYSICALLY_QUALIFIED',predecessor_sha256='fc9ceae01e8f1e86ebd326db92d0dbf6248e22621bbaed8e758b77bd9450c27e',
  typed_cancellation={'tag_bits':9,'valid_bits':1,'ack_bits':1,'identity':'fixedPC/current fenced local epoch and original native9bit tag','state_bits_added':0,'boundaries_added_bits_per_cycle':11,'throughput_entries_per_cycle':1,'latency_fault_free_added_cycles':0,'abort_drain_cost':'one receiving edge per native pending entry, up to16 plus accepted delayed ingress; committed writes still require actual PHY completion','protection':'same independently mirrored ingress pointers/counts/data and full-state equality; no cancellation from quarantined ambiguous ownership'},
  added_logic_reservation_um2=256,
  cancellation_semantics='Only after sticky controller abort; retire oldest physically unissued ingress entry on cancel_v&&cancel_take; never produce wd. Committed completion ledger untouched. Receiver clears handed ownership but keeps live ownership until global epoch fence.',
  epoch_additional_gate='native occupied count must reach zero through acknowledged typed cancellations before epoch_ready')
 m['cell_area_um2_estimate']+=256
 m['utilization_estimate']=m['cell_area_um2_estimate']/(m['floorplan_width_um']*m['floorplan_height_um'])
 return m
if __name__=='__main__':
 import json
 print(json.dumps(qwen_ctrl_write_cancel_model(),indent=2))

def qwen_ctrl_write_cancel_service_model():
 from uarch_model_qwen_ctrl_write_service import qwen_ctrl_write_service_model
 m=qwen_ctrl_write_service_model()
 m['leaves']=['qwen_ctrl_protected_model','qwen_ctrl_write_cancel_model']
 m['cell_reservation_um2']+=256
 m['frame_utilisation_reservation']=m['cell_reservation_um2']/m['frame_area_um2']
 m['typed_cancel_boundary_bits_per_cycle']=11
 m['typed_cancel_latency']='one pending entry per accepted cancellation edge after sticky abort; no fault-free addedcycle'
 m['abort']='Unissued native entries retire only through typed cancel_v/tag9/cancel_take. Actual committed writes still retire solely from matching true PHY completion. Bridge retains canceled live ownership until qualified global epoch fence.'
 return m
