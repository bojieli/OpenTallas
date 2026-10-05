"""Released recipe descriptor ROM compiler and prospective control sizing. No math VM."""
import argparse, ast, gzip, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
PROGRAM='results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz'
PROGRAM_SHA='ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354'
# IDs 0..16 are Boole's exact ABI. Remaining IDs route to other real services.
from tools.gpu_sys.canonical_qwen_native_opcode_abi import OPCODES, canonical_zero
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def compile_source():
    p=json.loads(gzip.decompress((ROOT/PROGRAM).read_bytes()))
    assert hashlib.sha256(canonical(p)).hexdigest()==PROGRAM_SHA
    assert len(p['operations'])==1737
    templates=sorted(p['microcode']); rows=[]
    for ti,t in enumerate(templates):
        nodes=p['microcode'][t]; steps=p['tile_kernel_ABI'][t]['steps']
        assert len(nodes)==len(steps)
        for step,(node,abi) in enumerate(zip(nodes,steps)):
            assert node['op']==abi['op']
            for sub,op in enumerate(abi['native_steps']):
                assert op in OPCODES
                # Exact source attrs, including NEG's mandatory three distinct RPCs.
                attrs={'dtype':'I64'} if node['op'] in ('IADD64','SHL64') else ({'dtype':'U32'} if node['op'] in ('IADD','ISUB','SHR','AND','OR','SELECT') else {})
                if node['op']=='NEG':attrs={'dtype':'U32'} if sub==1 else {}
                attr=2 if attrs.get('dtype')=='I64' else 1 if attrs.get('dtype')=='U32' else 3
                canon=canonical_zero(op,attrs)
                word=(int(canon)<<23)|(1<<22)|(ti<<18)|(step<<12)|(sub<<10)|(attr<<8)|OPCODES[op]
                rows.append(dict(id=len(rows),template=t,template_id=ti,ordered_step=step,substep=sub,lowered_primitive=op,opcode=OPCODES[op],attrs=attrs,canonical_zero=canon,source_node=node,source_contract=abi,word=f'{word:06x}'))
    masks=[]
    for pc,row in enumerate(p['operations']):
        assert row['pc']==pc
        masks.append(sum(1<<templates.index(t) for t in set(row['kernels'])))
    return dict(program_sha256=PROGRAM_SHA,source_operations=1737,templates=templates,opcodes=OPCODES,descriptors=rows,pc_template_masks=masks)
def sizing(d,endpoints):
    # Reuse the pinned unified model price without executing hardware inventories.
    uarch=(ROOT/'tools/uarch_model.py').read_bytes()
    dff=next(ast.literal_eval(n.value) for n in ast.parse(uarch).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DFF_UM2' for t in n.targets))
    ff_bits=(640+48)*72+30
    # Installed endpoint count explicit; root has 64 SM contexts, no extra TC bodies.
    return dict(schema='opentallas.native.controller.sizing.v1',program_sha256=PROGRAM_SHA,
      unified_model_source='tools/uarch_model.py',unified_model_sha256=hashlib.sha256(uarch).hexdigest(),
      default_enabled=False,adopt=False,status='ESTIMATE; no physical or token credit',endpoint_count=endpoints,
      memory=dict(operand_raw_bits=4*8192,result_raw_bits=8192,secded_word_bits=72,secded_data_bits=64,
                  operand_and_result_coded_bits=640*72,command_coded_bits=48*72,paired_control_state_bits=30,
                  descriptor_rom_bits=len(d['descriptors'])*24,pc_template_rom_bits=1737*13,
                  RF_page_bytes=512,RF_read_bytes_per_accept=512,RF_write_bytes_per_accept=512,
                  operand_max_pages=8,result_max_pages=2),
      compute=dict(MACs_per_cycle=0,primitive_lanes_per_beat=4,max_beats_per_primitive=32,fp32_pipeline_edges_add_mul=5,fp32_pipeline_edges_div_sqrt=31,conversion_extra_state_bits=0,fp32_arithmetic_pipeline_area_um2=None),
      boundaries=dict(RF_read_request_bits=18,RF_read_mirrored_result_bits=8192,RF_write_bits=4151,
                      RF_ACK_bits=55,datapath_operand_bits=1024,datapath_result_bits=256,
                      held_result_bits=8192,command_max_bits=48*64,tracks_required_sum_lower_bound=45000,
                      corridor_capacity=None,wire_stages=None,CDC_cycles=None),
      replication=dict(controller_per_endpoint=1,datapath_per_endpoint=1,operand_lane_selection_mux_inputs=128,
                       result_write_mux_inputs=32,descriptor_decode_rows=len(d['descriptors']),flag_fanout=4),
      floorplan=dict(DFF_um2_from_unified_model=dff,protected_holder_DFF_body_um2_ESTIMATE=ff_bits*dff,protected_holder_all_endpoints_DFF_body_um2_ESTIMATE=endpoints*ff_bits*dff,
                     movement_mux_body_um2_ESTIMATE=30099.73248,decode_mux_ECC_datapath_loaded_area_um2=None,area_um2=None,power_W=None,slot_fit=None,composed_area_um2=None,
                     coded_state_total_bits=endpoints*(640+48)*72,clock_tree_and_wire_area=None),
      serial_path=dict(local_clock='same enclosing clock; no private edge or clock',
          max_operand_RF_transactions=8,max_result_RF_transactions=2,
          no_stall_controller_formula='1 accept + 2*input_pages + ceil(elements/4)*(1 local beat OR 7 add/mul edges OR 33 div/sqrt edges) + 2*output_pages + visibility_wait + result_accept + reverse_accept; all backpressure/refresh/CDC/wire waits additional',
          refresh_credit_RTT=None,measured_cycles=None,whole_token_cycles=None,per_user_gain=None),
      unknowns='All area/power/route/loaded-clock/CDC/credit/refresh/context latency constants remain ESTIMATE; hardware size is prospective only; reject unsupported services.')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--endpoints',type=int,required=True);a=ap.parse_args()
    assert a.endpoints>0
    d=compile_source();a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'descriptors.json').write_bytes(canonical(d));(a.out/'model.json').write_bytes(canonical(sizing(d,a.endpoints)))
    (a.out/'descriptor.mem').write_text(''.join(r['word']+'\n' for r in d['descriptors']))
    (a.out/'pc_templates.mem').write_text(''.join(f'{m:04x}\n' for m in d['pc_template_masks']))
    print(json.dumps(dict(descriptors=len(d['descriptors']),PCs=1737,program_sha256=PROGRAM_SHA,endpoints=a.endpoints)))
if __name__=='__main__':main()
