"""Size and bind the stateless conversion component before RTL construction.

Shared dispatch is loaded as data; no checkpoint constructors or numerical VM.
--abi-source selects Dewey's authority or its committed historical snapshot.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

OPS = ('I2F', 'F2I', 'LDEXP', 'FP8_PACK', 'FP8_UNPACK')
INPUTS = (
 'results/uarch/c0_pc40_payload_lease_20261003/inputs/h3_qwen_bounded_native.py',
 'results/uarch/c0_pc40_payload_lease_20261003/inputs/h3_qwen_complete_native.py',
 'rtl/gpu_sys/ot_gpu_simt_lane.sv', 'rtl/abi3/ot_a3_format_pkg.sv',
 'tools/uarch_model.py',
 'results/uarch/w2_nc6_mutable_protection_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json')

def compose(root, abi_source):
    spec = importlib.util.spec_from_file_location('conversion_shared_abi', abi_source)
    abi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(abi)
    ids = {op: abi.dispatch(op, {})['opcode'] for op in OPS}
    if ids != dict(zip(OPS, range(21, 26))) or abi.TYPES != {'F32':0,'U32':1,'I64':2,'U8':3}:
        raise ValueError('shared conversion ABI changed: explicit migration required')
    if any(abi.ENGINE[op] != 'convert' for op in OPS):
        raise ValueError('shared engine delegation changed')
    constants={}
    for node in ast.parse((root/'tools/uarch_model.py').read_text()).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id=='UNCERTAINTY_PS':
                    constants[target.id]=ast.literal_eval(node.value)
    if constants.get('UNCERTAINTY_PS') != 60.0:
        raise ValueError('unified baseline setup policy changed')
    prices=json.loads((root/INPUTS[-1]).read_text())['facts']
    nand=prices['NAND2x1_ASAP7_75t_R']['SS']['area_um2']
    inv=prices['INVx1_ASAP7_75t_R']['SS']['area_um2']
    mux_price=3*nand+inv
    pins = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in INPUTS}
    # Source-sized barrel mux envelopes. Addition/priority/decode and loaded
    # routing remain explicit unpriced terms; this is not a complete area bound.
    mux_per_lane = 64*6*2 + 24*5*3
    return dict(schema='qwen-native-conversion-r1',source_pins=pins,
        shared_abi_sha256=hashlib.sha256(abi_source.read_bytes()).hexdigest(),
        opcode_bits=6,opcodes=ids,types=abi.TYPES,default_enabled=False,
        lanes=4,replicas_per_endpoint=1,endpoint_replica_count=None,
        MACs_per_cycle=0,elements_per_accepted_beat=4,
        carrier_bytes_per_operand=32,carrier_bytes_per_result=32,
        useful_bytes={'F32':16,'I64':32,'U8':4},
        boundary_data_bits_per_beat=3*256+256,
        boundary_control_bits=6+4*2+3+4+2+4+1,
        tracks_required_unshared=1052,channel_capacity_tracks=None,
        combinational_barrel_mux2_equivalents=4*mux_per_lane,
        mux_price_um2=mux_price,
        barrel_mux_area_partial_um2=4*mux_per_lane*mux_price,
        scalar_operand_mux2_equivalents=4*2*64,
        scalar_operand_mux_area_partial_um2=4*2*64*mux_price,
        opcode_fanout=4,type_fanout=4,fanout_buffer_area_um2=None,
        mux_estimate_scope='partial structural estimate, not a complete area bound',
        cell_price_basis='source SS NAND2/INV, 3NAND2+INV per2:1mux; loaded physical price unknown',
        unified_baseline='tools/uarch_model.py; additive conversion delegate, originals unchanged',
        additional_logic_area_um2=None,complete_area_um2=None,floorplan_slot_fit=None,
        new_storage_bits=0,new_macros=0,
        protected_operand_result_seats='existing Pauli controller, counted once',
        minimum_full128_accepted_beats=32,
        extra_registered_pipeline_edges=0,
        service_min_edges_full128=32,
        launch_ACK_CDC_RF_wait_edges=None,
        composed_token_latency=None,
        token_composition='actual conversion step element counts rounded up /4, plus source controller/RF/ACK/CDC waits; not zero-cost launch',
        SS_setup_delay_ps=None,FF_hold_delay_ps=None,
        setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        hardware_admission=False,
        blockers=['loaded SS/FF timing','complete cell and route/slot price','actual controller and RF service calendar'],
        semantics=dict(I2F='signed I64/unsigned U32/U8 to F32 RNE; F32 identity',
          F2I='F32 truncate toward zero to I64; nonfinite and abs>=2^63 fault',
          LDEXP='F32 plus signed32 exponent bits from I64/U32/U8; gradual RNE underflow, signed zero retained, nonfinite fault',
          FP8_PACK='existing E4M3FN RNE encoder; nonfinite fault before publication',
          FP8_UNPACK='existing exact format package; reserved127/255 fault; positive zero'),
        refused_types='F2I non-F32 and LDEXP/UNPACK floating exponent/code require explicit source enrollment')

def header(model):
    return '// Generated from Dewey shared six-bit ABI; do not truncate.\n'+''.join(
        f"localparam [5:0] OP_{op} = 6'd{model['opcodes'][op]};\n" for op in OPS)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--abi-source',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--header',type=Path)
    a=p.parse_args(); src=a.abi_source or a.root/'tools/gpu_sys/canonical_qwen_native_opcode_abi.py'
    m=compose(a.root,src); a.out.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    if a.header:a.header.write_text(header(m))

if __name__=='__main__':main()
