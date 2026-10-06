#!/usr/bin/env python3
"""One minimum port/control gate; reuse unchanged adopted numerical gates.

The explicit probe uses the production module's literal declaration. Its
two-edge latency is a test mechanism, NOT a numerical/latency measurement.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RTL = 'rtl/hbm_accel/integrated_20261006/ot_hbm_integrated_swiglu_quant_adapter.sv'
TB = 'rtl/test/hbm_accel/integrated_20261006/tb_hbm_integrated_swiglu_quant_adapter.sv'
ENGINE = 'rtl/hdc/v41x/ot_dsrom_su_swiglu.sv'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(cmd, log):
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    log.write_text(result.stdout + result.stderr)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = (ROOT / ENGINE).read_text()
    start = source.index('module ot_dsrom_su_swiglu #(')
    end = source.index('endmodule', start) + len('endmodule')
    module = source[start:end]
    header = module[:module.index(');')+2]
    probe = out / 'production_header_port_probe.sv'
    probe.write_text('`timescale 1ns/1ps\n' + header + '''
    // TEST ONLY: deliberate two-edge deterministic boundary golden.
    initial if(LM!=5 || LA!=4 || QLAT!=5 || NIN!=33 || NOUT!=23 || ROUTED!=1)
        $fatal(1,"adapter differs from selected adopted engine parameters");
    reg pending, valid_out, packet_fault;
    reg [8*W-1:0] codes;
    reg [10*W/32-1:0] scales;
    reg [16*W-1:0] bf16;
    assign vo=valid_out;assign q=codes;assign e=scales;assign y=bf16;
    assign fault=valid_out ? packet_fault : 1'bx;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin pending<=0;valid_out<=0;packet_fault<=0;end
        else begin
            pending<=v;valid_out<=pending;
            if(v)begin
                packet_fault<=lim[31];
                for(integer k=0;k<W;k=k+1)begin
                    codes[8*k+:8]<=g[32*k+:8];
                    bf16[16*k+:16]<=u[32*k+:16];
                end
                for(integer b=0;b<W/32;b=b+1)scales[10*b+:10]<=w[1024*b+:10];
            end
        end
    end
endmodule
''')
    configs = {'original': (ROOT/RTL).read_text()}
    configs['mutant_live_veto'] = configs['original'].replace(
        '.vo(q_valid),', '.vo(raw_valid),').replace(
        'wire engine_fault;', 'wire engine_fault, raw_valid;\n  assign q_valid=raw_valid && launch_permit;')
    configs['mutant_owner_truncation'] = configs['original'].replace(
        'assign q_frame=held_frame;', "assign q_frame={1'b0,held_frame[71:0]};")
    results = {}
    # Lightweight actual-source interface parse. -i leaves arithmetic primitives
    # unresolved deliberately; this is not a mapped/netlist or numerical gate.
    interface = run(['iverilog','-g2012','-i','-tnull','-s',
        'ot_hbm_integrated_swiglu_quant_adapter',
        '-Pot_hbm_integrated_swiglu_quant_adapter.ENABLE=1',
        '-Pot_hbm_integrated_swiglu_quant_adapter.N=32',str(ROOT/RTL),
        str(ROOT/ENGINE)], out/'production_interface_parse.log')
    if interface.returncode:
        raise RuntimeError(interface.stderr)
    recipe = {}
    for node in ast.parse((ROOT/'tools/dsrom_su_swiglu.py').read_text()).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in ('RTL','LIB','ADD6'):
                    recipe[target.id]=ast.literal_eval(node.value)
    files=recipe['RTL']+recipe['LIB']+[recipe['ADD6']]
    for name, rtl in configs.items():
        selected = ROOT/RTL if name == 'original' else out/(name+'.sv')
        if name != 'original':
            selected.write_text(rtl)
        binary = out/(name+'.vvp')
        compile_result = run(['iverilog','-g2012','-s',
            'tb_hbm_integrated_swiglu_quant_adapter','-o',str(binary),
            str(selected),str(ROOT/TB),str(probe)], out/(name+'_compile.log'))
        if compile_result.returncode:
            raise RuntimeError(compile_result.stderr)
        sim = run(['vvp',str(binary)], out/(name+'_run.log'))
        results[name] = dict(exit_code=sim.returncode,
            expected='PASS' if name=='original' else 'FAIL',
            observed='PASS' if sim.returncode==0 else 'FAIL')
        if (sim.returncode==0) != (name=='original'):
            raise RuntimeError(f'{name}: unexpected result\n{sim.stdout}{sim.stderr}')
        binary.unlink()
    record = dict(schema='hbm.swiglu-quant-adapter.boundary.v1',
        verdict='PASS_BOUNDARY_ONLY', source_revision='278a274e7',
        source_sha256={p:sha((ROOT/p).read_bytes()) for p in (RTL,TB,ENGINE)},
        canonical_swiglu_module_sha256=sha(module.encode()),
        production_interface_parse=dict(exit_code=interface.returncode,N=32,
            unresolved_primitive_mode=True,numerical=False),
        adopted_compile_contract=dict(recipe='tools/dsrom_su_swiglu.py::RTL+LIB+ADD6',
            files=files,source_sha256={p:sha((ROOT/p).read_bytes()) for p in files},
            requirement='Select ot_hdc_fastfp_lat_f12.sv ONCE for qmul/qadd wrappers; do not also compile generic fastfp_lat or blanket override native c12 ALAT6/MLAT6'),
        config=dict(N=1024,ROUTED=1,LM=5,LA=4,QLAT=5,NIN=33,NOUT=23),
        results=results,
        comparison='1024 G/U/weight words at actual production-header ports; 1024 code/BF16 words and 32 scales against independent deterministic boundary golden; full73 owner/cursor',
        control=['defaultOFF','reservation refusal','new-launch veto','warm accepted-output drain',
                 'masked plane3','valid-qualified fault','cold POR flush'],
        arithmetic_changed=False, arithmetic_gate_rerun=False,
        arithmetic_basis='results/rtl/dsrom_recovery_20261004/levers/su_swiglu.json',
        model_basis=['tools/uarch_model.py::hbm_swiglu_w2_private_join_model',
            'results/uarch/hubble_swiglu_w2_private_join_20261005/sizing.json',
            'results/rtl/hbm_su_fused_20261005/pre_rtl_price.json'],
        model_delta=dict(new_arithmetic_units=0,new_payload_bits=0,new_metadata_FF=0,
            new_cycles=0,new_clock_domains=0,existing_input_bits_per_issue=3*1024*32,
            existing_quant_bits_per_output=1024*24+32*10,
            parent_storage='Existing protected descriptor/landing/output cursor; no duplicate capture'),
        test_probe_edges=2, production_numeric_edges='Existing routed SwiGLU producer: 186, NOT the idx.q 89-cycle record',
        parent_joined=False, numerical_join_gate=False, contextual_SS_FF_qualified=False,
        limitations='Caller must supply held protected full73 owner, command-stable lim, real ordered landing cursor and whole accepted-output reservation; no completion/ACK/provider is fabricated. QDQ BF16 does not replace prequant norm y_data. RoPE remains Ptolemy; capture remains Franklin; HC ML6 remains separate.')
    (out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print('PASS_BOUNDARY_ONLY N1024; both meaningful mutants rejected; unchanged arithmetic gate reused')


if __name__=='__main__':
    main()
