#!/usr/bin/env python3
"""Native whole-SM scalar DIV source join proposal and priced incremental G0.
No RTL emitted or executed. Existing immutable source bytes are read by git ref.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
PARENT = '99da9b345cb7c9048b642f93517fb63729ff873a'
PINS = {}
def source(path):
    b = subprocess.check_output(['git','show',PARENT+':'+path],cwd=ROOT)
    PINS[path] = hashlib.sha256(b).hexdigest()
    return b


def compose_service(read_wait=0, write_wait=0, retire_wait=0):
    vals=(read_wait,write_wait,retire_wait)
    if any(type(x) is not int or x < 0 for x in vals):
        raise ValueError('explicit nonnegative stall edges required')
    return 37 + sum(vals)


def validate_command(c):
    keys={'opcode','a','b','dst','src_lane','dst_lane','denominator','input_version','destination_version','tree_complete','previous_retired'}
    if set(c)!=keys:
        raise ValueError('exact command fields required')
    if c['opcode']!='DIV' or c['denominator']!='45a00000':
        raise ValueError('source opcode or constant mismatch')
    if any(type(c[k]) is not int or not 0<=c[k]<512 for k in ('a','b','dst')):
        raise ValueError('RF slot outside aperture')
    if c['b']!=c['dst'] or any(type(c[k]) is not int or c[k]!=0 for k in ('src_lane','dst_lane')):
        raise ValueError('read-modify-write lane contract')
    if c['tree_complete'] is not True or c['previous_retired'] is not True:
        raise ValueError('incomplete tree or prior lease')
    if any(not isinstance(c[k],str) or not c[k] for k in ('input_version','destination_version')):
        raise ValueError('version identity required')
    return True


def merge_result(dst, y):
    if len(dst)!=128 or any(type(x) is not int or not 0<=x<=0xffffffff for x in dst+[y]):
        raise ValueError('128 source FP32 lanes required')
    return [y]+dst[1:]


class Lease:
    """Proposed software/source protocol; no claim of implemented hardware."""
    def __init__(self): self.state='idle'; self.command=None
    def accept(self,c):
        if self.state!='idle': raise ValueError('lease busy')
        validate_command(c); self.command=dict(c); self.state='read'
    def read_consumed(self):
        if self.state!='read': raise ValueError('read phase')
        self.state='execute'
    def result(self,fault):
        if self.state!='execute' or type(fault) is not bool: raise ValueError('result phase')
        self.state='failed' if fault else 'write'
    def write_ack(self):
        if self.state!='write': raise ValueError('write ACK phase')
        self.state='retire'
    def retire(self,version):
        if self.state not in ('retire','failed') or version!=self.command['destination_version']:
            raise ValueError('retirement before ACK or wrong version')
        success=self.state=='retire'; self.state='idle';self.command=None;return success
    def reset(self): self.state='idle';self.command=None


def model():
    PINS.clear()
    sm=source('rtl/gpu/ot_gpu_full_sm_service.sv').decode()
    rf=source('rtl/gpu/ot_gpu_rf_service.sv').decode()
    source('rtl/hdc/v41/ot_hdc_fdiv.sv')
    source('rtl/hdc/ot_hdc_sfu.sv')
    source('tools/h3_distributed_norm_endpoint.py')
    source('tools/h3_native_command_cost_contract.py')
    source('tools/w19_gpu_norm_calendar.py')
    source('tools/qwen_hbm_complete_executor.py')
    base=json.loads(source('results/uarch/full_sm_rf_service_20261002/model_final.json'))
    scalar=json.loads(source('results/uarch/h3_exact_scalar_contract_20261002/model.json'))
    for text, token in [(sm,'reg [4095:0] result_q'),(sm,'state==READ'),(sm,'state==ACK'),
                        (rf,'if(write_go) begin ack_valid<=1'),(rf,'rsp_b<=words_b[page_b]')]:
        if token not in text: raise ValueError('source join pattern changed')
    # Source body TT baseline plus explicit conservative incremental proxies.
    core=scalar['historical_physical_price']['DIV31_routed_standard_cell_area_um2']
    core_outline=scalar['historical_physical_price']['DIV31_routed_core_outline_um2']
    mux_bits=4096+32
    ledger={'DIV31_existing_TT_body':core,'result_RMW_mux_4128x0p2_proxy':mux_bits*.2,
            'extra_opcode_1bit_DFF':.2916,'control_buffer_proxy_reserve':512.0}
    extra=sum(ledger.values())
    models={}
    for target, b in base['models'].items():
        rect=b['proposed_expanded_logic_rectangle_um']
        width=rect[2]-rect[0]
        existing_area=b['logic_area_estimate_um2']
        total=existing_area+extra
        height=math.ceil((2*total/width)/2.16)*2.16
        proposed=[rect[0],rect[1],rect[2],rect[1]+height]
        capacity=width*(rect[3]-rect[1])*.5
        models[target]={'price_scope':'conditional if DIV enabled on this SM; Qwen RSTD needs no DIV',
          'Qwen_RSTD_DIV_calls':0, 'existing_logic_cell_um2_proxy':existing_area,
          'existing_expanded_slot_cell_capacity_um2':capacity,'extra_cell_um2_price':extra,
          'new_total_cell_um2_proxy':total,'existing_expanded_slot_fit':total<=capacity,
          'new_expanded_rectangle_um':proposed,'added_height_um':height-(rect[3]-rect[1]),
          'outline_height_um':b['retained_element_outline_um'][1],
          'inside_source_proposed_outline':proposed[3]<=b['retained_element_outline_um'][1],
          'physical_admission':False,'SM_replica_count_in_pinned_baseline':b['SM_replicas'],
          'all32SM_delta_cell_um2_if_one_DIV_each':32*extra,
          'collector_only_div_count_per_rank':1,'collector_only_selection_requires_Maxwell':True,
          'NS8_current_source_binding':None,'no_NS8_equals_eight_DIVs_assumption':True}
    return {'schema':'H3_NATIVE_DIV_SOURCE_JOIN_G0_PROPOSAL_V1','source_commit':PARENT,
      'source_sha256':dict(PINS),'status':'PRICED_SOURCE_JOIN_FOR_ADMISSION_NO_RTL',
      'owner':'Epicurus scalar DIV; Peirce compiler; Maxwell slot/service composition',
      'RTL_builds':0,'RTL_prepared':False,'physical_runs':0,'default_enabled':False,
      'source_body':'one unchanged ot_hdc_fdiv DEPTH31 per admitted conventional scalar endpoint; no divergent quotient implementation',
      'command_contract':{'opcode':'DIV','a':'completed tree result RF slot from compiler',
        'b':'same as dst: old destination vector for RMW','dst':'compiler scalar result home',
        'src_lane':0,'dst_lane':0,'denominator':'45a00000','constant_source':'w19_gpu_norm_calendar.scalar_norm_program @F5120',
        'input_version':'compiler completed chunk8 tree version','destination_version':'new rounded mean version',
        'tree_complete':True,'previous_retired':True,'actual_slots_from_compiler':None,
        'wire_versions':'one whole RF lease, one in-flight transaction; software versions cannot be aliased before ACK',
        'next_consumer':'epsilon FADD only after successful mirrored ACK/done; no reciprocal substitution'},
      'source_join':{'parent_copy':'future added opt-in service copy, current parent bytes preserved',
        'decode':'existing binary mul selector becomes 2-bit ADD/MUL/DIV opcode; defaultoff absent',
        'RF_read':'a=sum source vector, b=dst vector; whole provider lease excludes host changes',
        'capture':'at OPERATE&&rv copy rsp_b into existing4096bit result_q; launch DIV on rsp_a[31:0],45a00000',
        'execute':'WAIT_ALU branch uses original ADD/MUL valid for those opcodes and core vo for DIV',
        'result':'replace result_q[31:0] only; every other lane remains captured dst data',
        'success':'WRITE accepted -> registered mirrored ACK -> DONE held -> retire',
        'fault':'capture core fault, no successful write/publication; failed DONE held until retire. No fault accepted as success',
        'reset':'flush core valid line and parent control; invalidate done; payload not an architectural version',
        'pipeline_data_reset':'existing arithmetic payload unreset but vo gates capture; no invalid output retirement',
        'new_vector_register_bits':0,'existing_result_register_bits_reused':4096,
        'incremental_opcode_state_bits':1,'new_DIV_declared_state_bits':2634,
        'total_incremental_declared_register_bits':2635},
      'ports':{'new_RF_ports':0,'logical_read_B_per_accept':1024,'logical_write_B_per_success':512,
        'physical_mirrored_write_B_per_success':1024,'read_wires':8192,'write_wires':4096,
        'DIV_a_bits':32,'DIV_denominator_constant_bits':32,'DIV_output_payload_bits':32,
        'DIV_v_vo_fault_control_bits':3,'new_scalar_request_response_pin_incidence_bits':99,
        'parent_command_address_bits_reused':27,'extra_opcode_boundary_bits':1,
        'root_route_tracks_unchanged':41,'parent_RF_local_tracks_unchanged':12339,
        'global_shared_corridor_capacity_not_a_local_bus_qualification':True,
        'MUL_ADD_primitive_replicas_unchanged':128,'scalar_DIV_peak_ops_per_cycle_internal':1,
        'scalar_DIV_sustained_success_ops_per_edge_no_stall':1/38,
        'scalar_op_per_logical_RF_byte':1/1536,'MACs_per_cycle':0},
      'cost':{'incremental_cell_um2_ledger':ledger,'total_incremental_cell_um2':extra,
        'DIV_TT_outline_plus_incremental50pct_proxy_um2':core_outline+2*(extra-core),
        'proxy_basis':'uarch DFF0.2916,muxbit0.2,512control buffer reserve; DIV source-matched reachable body TT record. Proxies require actual mapping/SSFF before adoption.',
        'models':models,'clock_tree_PG_routing_via_extra_area_um2':None},
      'latency':{'success_accept_to_retire_no_stall_edges':compose_service(),
        'earliest_reaccept_edge_after_accept':38,'component_edges':{'admission':1,'RF_read':2,'execute_capture':31,'mirrored_write_ACK':2,'done_retire':1},
        'conditional_1p2GHz_service_ns':compose_service()/1.2,
        'fault_accept_to_retire_no_stall_edges':35,
        'all_stall_terms':'RF read, write admission, done retirement; command admission wait before accept additional',
        'finite_service_upper_bound_without_parent_ready_bounds':None,
        'whole_kernel_total_ns':None,'broadcast_delivery_fence_ns':None,
        'II1_core_not_service_II1':True,'no_ideal_collector_overlap':True},
      'clock':{'proposed_domain':'same native GPU service clock; no added CDC in endpoint',
        'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,'target_GHz':1.2,
        'source_depth_is_timing_qualification':False,
        'critical_paths':['RF clkQ -> lane0 source/normalizer -> DIV decode',
          '27 quotient compare/subtract stages','subnormal shift/sticky/RNE finish',
          'DIV output clkQ -> capture lane mux -> result FF','result FF -> RF mirrored write macro',
          'macro completion/ACK -> done/version retirement'],
        'if_stage_added':'reprice service/model first; no silent pipeline or uncertainty change'},
      'admission_required':['Maxwell current NS8 parent instance/source hooks and replica count',
        'Peirce exact completed-tree input slot and destination home binding',
        'actual local99pin escape/control fanout and new logic rectangle admission',
        'source-bound host/RF/write/done finite ready bounds and whole-kernel composer',
        'software compiler shared DIV constant/error/version contract',
        'reviewed sourcejoin/area/slot model before defaultoff RTL preparation',
        'fresh bounded source-bound GO before any compile; SSFF context after functional gate']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    b=json.dumps(model(),indent=2,sort_keys=True)+'\n'
    if a.out.exists() and a.out.read_text()!=b: raise SystemExit('immutable output changed; use fresh path')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(b)
