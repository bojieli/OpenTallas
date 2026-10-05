"""Generate a literal existing-engine enclosing top and pin-only Verilator driver.

Every leaf port is connected. Unjoined authorities remain external ports, never
constants. This does not add engine state, allocate new replicas, or admit P&R.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
W4 = 'results/uarch/Euclid_W4_RFACK_identity_contract_20261003/selfcontained-peer-r10/design/'
BLOCKS = (
 ('sector', 'rtl/model/qwen_payload_sector_authority_20261003/ot_gpu_qwen_payload_w2_authority.sv', 'ot_gpu_qwen_payload_w2_authority', 1, '.ENABLE(ENABLE),.IDENTW(207)'),
 ('kv', 'rtl/model/qwen_hbm_integrated_20261003/ot_gpu_qwen_joined_kv.sv', 'ot_gpu_qwen_joined_kv', 1, '.ENABLE(ENABLE)'),
 ('native', 'rtl/experimental/hbm_c0_connected_20261003/r5/ot_gpu_pc40_native_connector_r5.sv', 'ot_gpu_pc40_native_connector_r5', 1, '.ENABLE(ENABLE)'),
 ('sm', W4+'ot_gpu_full_sm_service.sv', 'ot_gpu_full_sm_service', 64, '.ENABLE(ENABLE),.ACK_ID(1)'),
 ('w2', 'rtl/experimental/w2_nc6_reset_quarantine_20261003/ot_w2_nc6_protected_completion_reset_quarantine.sv', 'ot_w2_nc6_protected_completion_reset_quarantine', 128, '.OPT_EXACT(ENABLE),.OPT_RESET_QUARANTINE(ENABLE),.PC_ID(7\'(i))'),
)
CONSTANTS = dict(NC=6, AW=34, CTAGW=32, GENW=4, PTAGW=35)


def leaf_ports(path, module):
    text = re.sub(r'//[^\n]*|/\*.*?\*/', '', path.read_text(), flags=re.S)
    match = re.search(r'\bmodule\s+'+module+r'\s*(?:#\s*\(.*?\)\s*)?\((.*?)\)\s*;', text, re.S)
    if not match:
        raise ValueError('Cannot extract literal header '+module)
    direction = width = None
    ports = []
    for raw in match[1].split(','):
        raw = raw.strip()
        decl = re.match(r'(input|output)\s+(?:wire|reg|logic)?\s*(?:\[([^\]]+)\])?\s*(\w+)$', raw)
        if decl:
            direction, rng, name = decl.groups()
            if rng:
                hi, lo = rng.split(':')
                if not re.fullmatch(r'[\w\s*+\-]+', hi+lo):
                    raise ValueError('unsupported range '+rng)
                width = eval(hi, {'__builtins__': {}}, CONSTANTS)-eval(lo, {'__builtins__': {}}, CONSTANTS)+1
            else:
                width = 1
        else:
            if not direction or not re.fullmatch(r'\w+', raw):
                raise ValueError('unsupported port '+raw)
            name = raw
        ports.append(dict(name=name, direction=direction, bits=width))
    return ports


def joined_kv():
    # Preserve the reviewed shared/state/metadata wiring and replace ONLY the
    # old owner55 reader leaf with Popper's actual fulloperator tuple bridge.
    # Neither peer wrapper is instantiated: exactly one original controller.
    src=ROOT/'rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_connected_ports.sv'
    original=src.read_text()
    module='ot_gpu_qwen_native_consumer_drain'
    bridge=ROOT/'rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_native_consumer_drain.sv'
    bridge_ports=leaf_ports(bridge,module)
    extra=[p for p in bridge_ports if p['name'].startswith(('native_','cohort_')) or p['name'] in ('rst_n','endpoint_fault','drain_retained')]
    header=[]
    for p in extra:
        rng='' if p['bits']==1 else f"[{p['bits']-1}:0] "
        header.append(f" {p['direction']} wire {rng}{p['name']},")
    original,n=re.subn(r' input wire  operation_valid,.*? output wire  reader_services_drained,', '\n'.join(header), original, flags=re.S)
    if n!=1:raise ValueError('reviewed reader header changed')
    connections=[]
    for p in bridge_ports:
        name=p['name']
        if name.startswith(('consumer_','drain_')) and name!='drain_retained':expression='c_'+name
        elif name=='fault':expression='reader_fault'
        elif name=='run_enable':expression='effective_enable'
        elif name=='endpoint_fault':expression='endpoint_fault || core_fault || router_fault || observer_fault || join_fault'
        else:expression=name
        connections.append(f'.{name}({expression})')
    replacement=f'{module} #(.ENABLE(ENABLE)) native_consumer_drain(\n  '+',\n  '.join(connections)+'\n );'
    original,n=re.subn(r'ot_gpu_qwen_kv_reader_services #\(\.ENABLE\(ENABLE\)\) reader_services \(.*?\n \);', replacement, original, flags=re.S)
    if n!=1:raise ValueError('reviewed reader instance changed')
    original=original.replace('module ot_gpu_qwen_kv_connected_ports ', 'module ot_gpu_qwen_joined_kv ')
    original='// Source-derived join: Dewey73d8 individual modules + Popperdf414 bridge; ONE controller.\n'+original
    (OUT/'ot_gpu_qwen_joined_kv.sv').write_text(original)


def main():
    joined_kv()
    pins = {'stream_clk': dict(direction='input', bits=1, count=1, leaf='clk'), 'assembly_enabled': dict(direction='output', bits=1, count=1, leaf='ENABLE')}
    instances = []
    internal = []
    shared = dict(service_valid='scratch_valid', service_write='scratch_write', service_addr='scratch_addr', service_wdata='scratch_wdata', service_ready='scratch_ready', service_done='scratch_done', service_rdata='scratch_rdata', service_done_ready='scratch_done_ready')
    selected = dict(caller_req_v='c_req_v', caller_req_we='c_req_we', caller_req_addr='c_req_addr', caller_req_tag='c_req_tag', caller_req_gen='c_req_gen', caller_rsp_rdy='c_rsp_rdy', caller_wr_done_rdy='c_wr_done_rdy', raw_rsp_v='c_rsp_v', raw_wr_done_v='c_wr_done_v', raw_rsp_tag='c_rsp_tag', raw_wr_done_tag='c_wr_done_tag', raw_rsp_gen='c_rsp_gen', raw_wr_done_gen='c_wr_done_gen')
    for prefix, source, module, count, params in BLOCKS:
        ports = leaf_ports(ROOT/source, module)
        connection = []
        for p in ports:
            name, bits = p['name'], p['bits']
            if name == 'clk':
                expression = 'stream_clk'
            else:
                target = prefix+'_'+name
                pins[target] = dict(direction=p['direction'], bits=bits*count, count=count, leaf_bits=bits, leaf=name, block=prefix)
                expression = target if count == 1 else (target+'[i]' if bits == 1 else target+f'[i*{bits} +: {bits}]')
            if prefix=='kv' and name in shared:
                pins.pop('kv_'+name)
                expression='sm_'+shared[name]
            if prefix=='sm' and name in shared.values() and p['direction']=='input':
                pins[prefix+'_'+name]['direction']='output'
            if prefix=='sector' and name in selected:
                target='sector_'+name
                pins.pop(target)
                expression=f"w2_{selected[name]}[selected_PC*{bits} +: {bits}]"
            elif prefix=='sector' and name=='raw_req_rdy':
                pins.pop('sector_raw_req_rdy'); expression='raw_w2_req_rdy[selected_PC*6 +: 6]'
            elif prefix=='sector' and name=='bus_PC':
                pins.pop('sector_bus_PC'); expression='selected_PC'
            elif prefix=='w2' and name=='c_req_rdy':
                expression='raw_w2_req_rdy[i*6 +: 6]'
            elif prefix=='w2' and name in ('c_req_v','c_rsp_rdy','c_wr_done_rdy'):
                expression=f'guarded_{name}[i*6 +: 6]'
            connection.append(f'.{name}({expression})')
        instance = f'{module} #({params}) u_{prefix}(\n  '+',\n  '.join(connection)+'\n );'
        if count != 1:
            instance = f'for(genvar i=0;i<{count};i=i+1) begin:g_{prefix}\n '+instance+'\n end'
        instances.append(instance)
    lines = ['// Existing-engine assembly only; external authority ports are intentionally explicit.',
             '// ENABLE=0 by default. No external fence/ready/ACK is tied to a constant.',
             '`timescale 1ps/1ps', 'module ot_gpu_qwen_hbm_integrated #(parameter bit ENABLE=0)(']
    declarations = []
    for name, p in pins.items():
        rng = '' if p['bits']==1 else f"[{p['bits']-1}:0] "
        declarations.append(f" {p['direction']} wire {rng}{name}")
    lines.extend([',\n'.join(declarations), ');', '''assign assembly_enabled=ENABLE;
wire [6:0] selected_PC = sector_grant_live ? sector_grant_identity[45:39] : sector_map_PC;
wire [767:0] raw_w2_req_rdy,guarded_c_req_v,guarded_c_rsp_rdy,guarded_c_wr_done_rdy;
for(genvar p=0;p<128;p=p+1)begin:g_guard
 wire [5:0] req_mask = selected_PC==p ? sector_req_permit : 6'b111111;
 wire [5:0] cap_mask = selected_PC==p ? sector_capture_permit : 6'b111111;
 assign guarded_c_req_v[p*6+:6]=w2_c_req_v[p*6+:6]&req_mask;
 assign w2_c_req_rdy[p*6+:6]=raw_w2_req_rdy[p*6+:6]&req_mask;
 assign guarded_c_rsp_rdy[p*6+:6]=w2_c_rsp_rdy[p*6+:6]&cap_mask;
 assign guarded_c_wr_done_rdy[p*6+:6]=w2_c_wr_done_rdy[p*6+:6]&cap_mask;
end''', '\n'.join(instances), 'endmodule', ''])
    (OUT/'ot_gpu_qwen_hbm_integrated.sv').write_text('\n'.join(lines))
    deps = ['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'] + [W4+n for n in ('ot_gpu_rf_service.sv','ot_gpu_full_sm_service.sv','ot_gpu_scratch_service.sv','ot_gpu_fadd.sv','ot_hdc_fp32_add_lat.sv','ot_hdc_fp32_mul_lat.sv','ot_hdc_fastfp.sv','ot_hdc_prefix.sv','ot_sram_1r1w_128x256_m1_r2c2.v','ot_sram_1r1w_1024x256_m2_r2c2.v')]
    deps += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'rtl/experimental/hbm_c0_connected_20261003/r5').glob('*.sv'))]
    deps += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'rtl/model/qwen_kv_connections_20261003').glob('*.sv')) if p.stem not in ('ot_gpu_qwen_kv_connected_ports','ot_gpu_qwen_kv_reader_services')]
    deps += ['rtl/model/qwen_hbm_integrated_20261003/ot_gpu_qwen_joined_kv.sv', 'rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_native_consumer_drain.sv']
    deps += ['rtl/experimental/hbm_c0_connected_20261003/r2/ot_gpu_c0_fmax_leaf_r2.sv', 'rtl/gpu/w6/ot_gpu_rf_visibility_fence_w6.sv', 'rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv', 'rtl/experimental/w2_nc6_reset_quarantine_20261003/ot_w2_nc6_protected_completion_reset_quarantine.sv', 'rtl/model/qwen_payload_sector_authority_20261003/ot_gpu_qwen_payload_w2_authority.sv', 'rtl/model/qwen_payload_sector_authority_20261003/ot_gpu_qwen_payload_sector_authority.sv',
             'rtl/experimental/w2_nc6_reset_quarantine_20261003/ot_w2_nc6_coded_secondary_reset_quarantine.sv',
             'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv', 'rtl/experimental/w2_nc6_correction_control_split_20261003/ot_w2_nc6_correction_control.sv']
    deps += ['rtl/model/qwen_hbm_integrated_20261003/ot_gpu_qwen_hbm_integrated.sv']
    (OUT/'sources.f').write_text('\n'.join(dict.fromkeys(deps))+'\n')
    manifest = dict(top='ot_gpu_qwen_hbm_integrated', pins=pins,
                    source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in deps},
                    inventory=dict(rank_count=2, SM_per_rank=32, W2_PC_count=128, native_connector_count=1, KV_controller_count=1),
                    derivation_inputs_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_connected_ports.sv','rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_native_consumer_drain.sv')},
                    scope='literal reuse; native r5 is PC40 FMIN, NOT complete canonical operator dispatch',
                    unresolved=['native RF-to-selected SM arbitration/source ownership', 'native shared contender source binding',
                                'physical source allocator/prior-sector+selected-client drain proof', 'actual W2 state-write/capture/visibility/reverse observer enrollment',
                                'source fulloperator accepted consumer and individual eight-cohort endpoints', 'real backend and request/reverse CDC',
                                'source issuer allocation, reset/quiescence enrollment', 'complete1737 operator dispatcher'],
                    streaming_clock_period_ps='2500/3', setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                    physical_qualified=False, token_qualified=False)
    (OUT/'ports.json').write_text(json.dumps(manifest, indent=2)+'\n')
    cpp = ['#include "Vot_gpu_qwen_hbm_integrated.h"', '#include "verilated.h"',
           '#include <iostream>', '#include <sstream>', '#include <iomanip>', '#include <string>', '#include <vector>', '#ifndef CANONICAL_ENABLE', '#define CANONICAL_ENABLE 0', '#endif',
           'static std::vector<uint32_t> unpack(std::string s, unsigned bits) {',
           ' if(s.empty() || s.size()>(bits+3)/4) throw std::runtime_error("width");',
           ' std::vector<uint32_t> v((bits+31)/32,0);',
           ' for(unsigned i=0;i<s.size();i++){char c=s[s.size()-1-i]; unsigned n;',
           " if(c>='0'&&c<='9')n=c-'0'; else if(c>='a'&&c<='f')n=c-'a'+10;else throw std::runtime_error(\"hex\");",
           ' v[i/8]|=n<<((i%8)*4);}',
           ' if(bits%32 && (v.back()>>(bits%32)))throw std::runtime_error("width");return v;}',
           'static void word(uint32_t v){std::cout<<std::hex<<std::setfill(\'0\')<<std::setw(8)<<v;}',
           'int main(int argc,char**argv){VerilatedContext context;context.commandArgs(argc,argv);',
           ' Vot_gpu_qwen_hbm_integrated dut(&context); std::string line; unsigned half=0; const unsigned delta[6]={416,417,417,416,417,417};',
           ' while(std::getline(std::cin,line)){try{std::istringstream in(line);std::string op,name,value,extra;in>>op;',
           ' if(op=="HELLO"){dut.eval();std::cout<<"ot_gpu_qwen_hbm_integrated ENABLE="<<unsigned(dut.assembly_enabled)<<" SM=64 W2=128";}',
           ' else if(op=="EVAL"){if(in>>extra)throw std::runtime_error("extra");dut.eval();std::cout<<"OK";}',
           ' else if(op=="EDGE"){if(in>>extra)throw std::runtime_error("extra");dut.stream_clk=0;dut.eval();context.timeInc(delta[half++%6]);dut.stream_clk=1;dut.eval();context.timeInc(delta[half++%6]);dut.stream_clk=0;dut.eval();std::cout<<"OK";}',
           ' else if(op=="GET"){in>>name;if(in>>extra)throw std::runtime_error("extra");']
    for name, p in pins.items():
        b=p['bits']; getter=f'word(dut.{name});' if b<=32 else (f'word(uint32_t(dut.{name}>>32));word(uint32_t(dut.{name}));' if b<=64 else f'for(int i={(b+31)//32-1};i>=0;i--)word(dut.{name}[i]);')
        cpp.append(f' if(name=="{name}"){{{getter}}} else')
    cpp += [' throw std::runtime_error("unknown pin");}', ' else if(op=="SET"){in>>name>>value;if(in>>extra)throw std::runtime_error("extra");']
    for name, p in pins.items():
        if p['direction']!='input' or name=='stream_clk':continue
        b=p['bits']; setter=f'dut.{name}=v[0];' if b<=32 else (f'dut.{name}=uint64_t(v[0])|(uint64_t(v[1])<<32);' if b<=64 else f'for(unsigned i=0;i<v.size();i++)dut.{name}[i]=v[i];')
        cpp.append(f' if(name=="{name}"){{auto v=unpack(value,{b});{setter}std::cout<<"OK";}} else')
    cpp += [' throw std::runtime_error("unknown/output pin");}', ' else throw std::runtime_error("command");',
            ' std::cout<<"\\n"<<std::flush;}catch(const std::exception&e){std::cout<<"ERR "<<e.what()<<"\\n"<<std::flush;return 2;}}dut.final();return 0;}', '']
    (OUT/'pin_driver.cpp').write_text('\n'.join(cpp))

if __name__=='__main__':main()
