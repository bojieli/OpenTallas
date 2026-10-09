"""Model-first Qwen r25 TOKEN18 candidate. No physical closure claim."""
import json
import ast
from pathlib import Path
# Read the unified calibrated FF constant without executing unrelated ledgers.
_nodes = ast.parse(Path(__file__).with_name("uarch_model.py").read_text()).body
DFF_UM2 = next(ast.literal_eval(n.value) for n in _nodes if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DFF_UM2" for t in n.targets))

def model():
    return dict(schema='opentallas.qwen_r25_cmdproc18.v1',status='CANDIDATE_NOT_ADOPTED',
      source_base='961688ad8', token_bits=18,vocabulary=151936, replicas_per_die=2,
      macs_per_cycle=0, compute_intensity=0,
      ports_bytes_per_cycle=dict(command_write=8,command_read=8,result_per_sm=4),
      boundary_bits=dict(doorbell_tuple_old=147,doorbell_tuple_new=148,split_link=148,
                         loader_old=341,loader_new=343,su_token_old=17,su_token_new=18),
      register_delta_bits_per_die=29,
      register_delta=dict(north_xl_input_stages=3,south_xl_output_stages=2,south_loader_input_stages=6,core_launch_completion=4,completion_sinks=2,su_zero_to_signal_stages=12),
      area=dict(ff_body_proxy_um2=29*DFF_UM2,logic_reservation_um2=128,
                at_55pct_proxy_um2=(29*DFF_UM2+128)/.55,
                slot_fit='far below 0.60mm2 cmdproc estimate; route not measured'),
      replicas_mux_fanout='two existing processors; +1 token launch FF and completion FF each; 4 SU token publications, no new mux or replica; unchanged SM face PC-only launch',
      routing=dict(extra_signal_tracks=4,capacity='existing split xl grows 1 bit and loader 2 bits; pin/route capacity must be requalified; SU uses spare 64-bit payload'),
      latency=dict(added_token_cycles=0,added_command_cycles=0,base_sram_RDREG=2),
      embedding=dict(row_bytes=4096,max_token=151935,max_int8_byte_offset=151935*4096,
                     scale_row_bytes=2,max_scale_byte_offset=151935*2,
                     address_bits=64,cycles_delta=0),
      performance='correctness enablement only; no speedup credit',
      scope='Qwen host/program/cmdproc candidate; DS full73 PCWB contracts remain TOKEN17')

if __name__=='__main__': print(json.dumps(model(),indent=2))
