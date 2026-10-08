"""Conservative model-before-RTL for a fail-closed single-PC replica guard."""
from uarch_model_qwen_ctrl_shift import model as shift_model
import uarch_model as unified

def model():
    base=shift_model()
    leaf_w,leaf_h=base['frame_um']; guard_w=64.0
    frame=[2*leaf_w+guard_w,leaf_h]
    return dict(schema='opentallas.qwen_ctrl_protected.v1',status='PROPOSED_NOT_ADOPTED',
      model_precedes_rtl=True,source_model='tools/uarch_model_qwen_ctrl_protected.py',
      replicas=128,controller_copies_per_pc=2,controller_copies_total=256,
      macs_per_cycle=0,compute_intensity_macs_per_byte=0,
      fault_model='one sequential-state bit upset in one controller replica or one guard sticky-state bit; no simultaneous common-mode, clock, reset, input-wire or combinational faults',
      isolation='independent retained replicas; synthesis/mapping must prove no shared state roots',
      memory_ports=base['memory_ports'],
      boundary_bits=base['boundary_bits'],
      internal_boundary_bits_per_cycle=dict(command_input_fanout=72,qualified_output_packet_each=43,total_output_compare=86),
      routing=dict(max_final_wire_um=100,guard_width_um=guard_w,placement='two full controller leaves with output faces toward central guard; mirror right leaf',tracks_per_face=128,tracks_available_per_face=int(leaf_h/.288)),
      replica_mux_cost='43 equality XOR/XNOR bits and balanced reduction; gates all emitted fields, valid, write enable and returned credits; two separately retained sticky-halt bits',
      replica_fanout_cost='incoming command/read-credit fanout2; clock and reset distribution must qualify actual three-region context',
      area=dict(frame_um=frame,cell_reservation_um2=2*base['area']['cell_bound_um2']+1024+2*unified.DFF_UM2,
        guard_logic_reservation_um2=1024,frame_area_per_pc_um2=frame[0]*frame[1],
        total_frame_increment_um2=128*(frame[0]-leaf_w)*leaf_h,utilisation_target=.55,
        measured=False),
      latency=dict(added_cycles=0,added_token_cycles=0,output_logic_depth='43bit equality balanced tree plus fail-closed field gates; actual SS/FF gate delay unmeasured',
        command_data_alignment='no stage added to any JEDEC command; external write-data alignment unchanged in fault-free operation',
        credit_reservation='unchanged eight ingress credits and same-cycle return; no delayed credit added; after fault no new credits emitted',
        refresh='no added command cycle, so first and later refresh timestamps equal pinned controller; baseline DRAM startup epoch and parent fault-refresh handoff still require binding'),
      energy=dict(controller_activity_factor_bound=2,extra_compare_bits_per_cycle=43,joules_unmeasured=True),
      adoption_blocks=['physical SS/FF plus actual load','preserved independent mapped state','runtime fault containment gate','parent fault abort and already-issued write drain','external PHY valid/NOP binding','startup refresh epoch contract'],
      physical_phy_scope='same row_v/col_v accepted-command contract as ot_qwen_hbm_stream_ack; no pin-level CA encoder claim')
if __name__=='__main__':
    import json
    print(json.dumps(model(),indent=2))
