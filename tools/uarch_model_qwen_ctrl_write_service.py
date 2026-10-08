"""Composition before build: protected controller + native ownership receiver."""
def qwen_ctrl_write_service_model():
    from uarch_model_qwen_ctrl_protected import model as controller_model
    from uarch_model_qwen_ctrl_write_ledger import qwen_ctrl_write_ledger_model
    ctl=controller_model(); ledger=qwen_ctrl_write_ledger_model()
    width=ctl['area']['frame_um'][0]+ledger['floorplan_width_um']
    height=max(ctl['area']['frame_um'][1],ledger['floorplan_height_um'])
    cells=ctl['area']['cell_reservation_um2']+ledger['cell_area_um2_estimate']+128+2*.2916
    return dict(status='SIZED_NOT_ADOPTED',replicas=128,macs_per_cycle=0,
      leaves=['qwen_ctrl_protected_model','qwen_ctrl_write_ledger_model'],
      additional_state_bits_per_pc=2,additional_logic='10-bit requested bank/column equality, opcode gate and two independently retained sticky contract-fault rails',
      extra_logic_reservation_um2=128,extra_ff_area_um2=2*.2916,
      command_ingress_bits_per_cycle=33,command_return_bits_per_cycle=1,
      read_credit_bits_per_cycle=3,native_write_bits_per_cycle=290,
      native_done_bits_per_cycle=10,physical_command_bits_per_cycle=40,
      physical_write_bits_per_cycle=289,
      routing=dict(extra_comparison_tracks=20,guard_corridor_width_um=64,track_pitch_um=.288,available_tracks=222),
      frame_um=[width,height],frame_area_um2=width*height,target_frame_area_mm2=128*width*height/1e6,
      cell_reservation_um2=cells,frame_utilisation_reservation=cells/(width*height),
      retained_ff_per_pc=4712+ledger['retained_ff_per_pc']+2,
      retained_ff_basis='protected150 generic synthesis4712 plus mirrored ledger model and two newcontract rails; mapped composition unmeasured',
      memory_port_bytes_per_cycle=dict(native_input=32,physical_write=32,mirrored_ingress_write=64),
      frame_basis='side-by-side protected-controller and ledger initial slots; final placement and pin-station distances unqualified',
      latency_added_cycles=0,single_user_token_added_cycles=0,
      flow='Parent arbitrates descriptors/go and offered ledger WR packets with eight initial controller credits. Ledger handoff occurs only when matching WR command is admitted. No independent ready response or duplicate scheduler.',
      mutable_state='two contract-fault rails; same single sequential upset scope as both leaves; actual mapped retention pending',
      abort='Ledger stop suppresses controller ingress, returned credits and emitted commands. Protected controller fault drives ledger abort; committed writes retain true completion custody.',
      reset='Cold reset only with no physical transactions. Sticky controller/guard faults are not reset by epoch_advance. External refresh owner and cold recovery remain required.',
      energy='two additional guard FF and10 comparison bits percycle; mapped power pending',
      adoption_blocks=['Leaf physical closure','Actual mapped independent state and guard retention','External protected refresh owner','Native bridge CDC and global old-epoch transport drain/cancellation including previously issued reads','Actual die composition and station pin distances'])
if __name__=='__main__':
 import json
 print(json.dumps(qwen_ctrl_write_service_model(),indent=2))
