"""Minimal source I8 profile enrollment and additive pre-RTL sizing.

U8 is a byte carrier only when signed_i8_mask is set. The semantic dtype stays
I8 in the immutable shape contract. No numerical casts or checkpoint loading.
Pauli/Dewey own installed capture/protection/transport of this explicit mask.
"""
import argparse,ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
VM='results/uarch/c0_pc40_payload_lease_20261003/inputs/h3_qwen_bounded_native.py'
COMPLETE='results/uarch/c0_pc40_payload_lease_20261003/inputs/h3_qwen_complete_native.py'
PRICES='results/uarch/w2_nc6_mutable_protection_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json'
PINS=(VM,COMPLETE,'results/uarch/c0_pc40_payload_lease_20261003/inputs/qwen3_deployment_quality.py',
      'results/uarch/c0_pc40_payload_lease_20261003/inputs/qwen_hbm_complete_executor.py',
      'tools/gpu_sys/canonical_qwen_native_opcode_abi.py',
      'rtl/gpu/native/ot_gpu_native_conversion.sv','rtl/gpu/native/ot_gpu_native_conversion_abi.svh',
      'rtl/abi3/ot_a3_format_pkg.sv','rtl/gpu_sys/ot_gpu_simt_lane.sv',
      'tools/uarch_model.py',PRICES)

def i2f_profile(source_dtype, *, source_op='I2F'):
    from tools.gpu_sys.canonical_qwen_native_opcode_abi import TYPES,OPCODES
    if source_op not in ('I2F','ITOF') or source_dtype not in (*TYPES,'I8'):
        raise ValueError('unbound source signed-byte conversion profile')
    signed=source_dtype=='I8'
    return dict(source_dtype=source_dtype,carrier_type=TYPES['U8'] if signed else TYPES[source_dtype],
                signed_i8_mask=int(signed),opcode=OPCODES['I2F'],
                profile_semantics='signed two-complement byte' if signed else source_dtype,
                command_profile_bits=4,profile_scope='operand0 only for I2F',
                requires_independent_immutable_profile_match=True)

def validate_profile(*,source_dtype,carrier_type,signed_i8_mask,opcode):
    expected=i2f_profile(source_dtype)
    if type(signed_i8_mask) is not int or signed_i8_mask!=expected['signed_i8_mask'] or carrier_type!=expected['carrier_type'] or opcode!=expected['opcode']:
        raise ValueError('source dtype/carrier/signed mask/opcode mismatch')
    return expected

def method(source, cls, name):
    t=ast.parse(source)
    c=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name==cls)
    return ast.get_source_segment(source,next(n for n in c.body if isinstance(n,ast.FunctionDef) and n.name==name))

def compose(root):
    vm=(root/VM).read_text();complete=(root/COMPLETE).read_text()
    if hashlib.sha256(vm.encode()).hexdigest()!='282e57ab97f2dcdd0205b6f4e11ec189b669e3cc48548fab5f6d3c373d63c32b':
        raise ValueError('frozen native VM changed')
    read=method(vm,'HBMByteTileProvider','read_tile');provider=method(vm,'TiledMachine','provider')
    primitive=method(vm,'NativePrimitiveVM','primitive')
    if read.count('np.frombuffer(data,np.int8)')!=1 or 'np.frombuffer(payloads[0],np.int8)' not in read or 'dtype!=np.int8' not in provider or "elif op=='I2F': v=a[0].astype(F)" not in primitive:
        raise ValueError('actual signed provider/I2F source contract changed')
    recipe=ast.get_source_segment(complete,next(n for n in ast.parse(complete).body if isinstance(n,ast.FunctionDef) and n.name=='recipe'))
    if "ins('ITOF', 'decoded', 'codes')" not in recipe or "ins('ITOF', 'w', 'w_codes')" not in recipe:
        raise ValueError('released EMBED/MATRIX source recipes changed')
    q=(root/PINS[2]).read_text()
    quant=ast.get_source_segment(q,next(n for n in ast.parse(q).body if isinstance(n,ast.FunctionDef) and n.name=='quantize_w8'))
    if 'torch.int8' not in quant:raise ValueError('released W8 producer codec changed')
    facts=json.loads((root/PRICES).read_text())['facts']
    nand=facts['NAND2x1_ASAP7_75t_R']['SS']['area_um2'];inv=facts['INVx1_ASAP7_75t_R']['SS']['area_um2']
    dff=next(ast.literal_eval(n.value) for n in ast.parse((root/'tools/uarch_model.py').read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DFF_UM2' for t in n.targets))
    return dict(schema='qwen-native-signed-i8-r1',source_required=True,
        source_census_basis='actual released W8 producer + byte-provider decode + tiled dtype refusal + EMBED/MATRIX ITOF recipes + frozen VM I2F cast; no JSON dtype-key inference',
        source_profiles=['EMBED.codes:I8 -> ITOF:F32','MATRIX.w_codes:I8 -> ITOF:F32'],
        source_pins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in PINS},
        global_opcode_bits=6,I2F_opcode=21,carrier_type_bits=2,
        semantic_type='I8; distinct from U8 by explicit protected source-profile mask',
        endpoint_profile='a_signed_i8; actual immutable source I8 required',
        command_mask_bits=4,authority_mask_bits=4,mask_other_operands='zero; not enrolled',
        lanes=4,MACs_per_cycle=0,carrier_bytes_per_operand_beat=32,result_bytes_per_beat=32,
        useful_input_bytes_per_beat=4,endpoint_extra_boundary_bits=1,endpoint_extra_tracks=1,
        controller_extra_boundary_bits=8,channel_capacity=None,
        replicas_per_endpoint=1,selected_endpoint_replicas=64,
        incremental_mux2_equivalents=4*64+2,
        incremental_mux_area_partial_um2=(4*64+2)*(3*nand+inv),
        estimated_profile_decode_gate_area_um2=8*nand+4*inv,
        estimate_basis='one 64bit sign-extension select/lane + two type-bit selects; 8NAND2+4INV decode allowance; wires repeat source bit7, no adder',
        component_new_state_bits=0,component_new_clock_reset_sinks=0,
        controller_prospective_profile_retention_bits=8,
        controller_retention_reservation_um2=8*dff,
        full64_mux_decode_area_partial_um2=64*((4*64+2)*(3*nand+inv)+8*nand+4*inv),
        full64_controller_retention_reservation_um2=64*8*dff,
        full64_component_extra_tracks=64,
        controller_SECDED_increment=None,
        protection_policy='Pauli must allocate captured mask and independently observed authority mask in actual protected command; no free padding assumed',
        complete_loaded_increment_um2=None,floorplan_fit=None,
        baseline_conversion_body='existing full converter once; no duplicate area charge',
        added_registered_pipeline_edges=0,minimum_full128_beats=32,
        launch_RF_ACK_CDC_waits='unchanged actual owner services; unknown composed calendar retained',
        SS_setup_delay=None,FF_hold_delay=None,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        full_token_latency=None,default_off=True,hardware_admission=False,
        implementation_join='Pauli protected source-mask/immutable profile comparison and Dewey rawbyte/cmd mask transport pending; no implicit installed claim')

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(compose(a.root),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
