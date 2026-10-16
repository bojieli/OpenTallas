#!/usr/bin/env python3
"""Lightweight full128 W16 RTL rail gate with externally scheduled controls."""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import tempfile

from area_benes_routes import compile_route, complete_assignment, expected_output

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / 'tools/s81_vm/area_benes_rail.sv'
OUT = ROOT / 'results/arch/s81_vm_area_1417/benes_rail.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack(words, width):
    return sum(word << (i * width) for i, word in enumerate(words))


def main():
    rng = random.Random(1417)
    assignments = [list(range(53)), list(range(95, 42, -1)),
                   [(s * 37 + 17) % 96 for s in range(53)], rng.sample(range(96), 53)]
    permutations = [complete_assignment(a) for a in assignments]
    for _ in range(100):
        p = list(range(128))
        rng.shuffle(p)
        permutations.append(p)
    inputs, expected, controls = [], [], []
    for frame, p in enumerate(permutations):
        # bit15 valid, bits14:7 frame tag, bits6:0 source identity.
        # First four frames model 53 live inputs and 75 distinguishable pads.
        words = [((int(s < 53) if frame < 4 else 1) << 15) |
                 ((frame & 255) << 7) | s for s in range(128)]
        inputs.append(pack(words, 16))
        expected.append(pack(expected_output(p, words), 16))
        controls.append(pack([pack(row, 1) for row in compile_route(p)], 64))
    count = len(permutations)
    tb = f'''`timescale 1ns/1ps
module tb;
 reg ck=0;
 reg [2047:0] idata;
 reg [831:0] controls;
 wire [2047:0] odata;
 reg [2047:0] inputs[0:{count-1}];
 reg [2047:0] expected[0:{count-1}];
 reg [831:0] routes[0:{count-1}];
 integer e,s,k,checked=0;
 reg mut_control,mut_data;
 s81_area_benes_rail dut(.ck_stage({{13{{ck}}}}),.i_data(idata),
   .i_stage_sw(controls),.o_data(odata));
 initial begin
   mut_control=$test$plusargs("MUTANT_CONTROL");
   mut_data=$test$plusargs("MUTANT_DATA");
   $readmemh("input.hex",inputs);
   $readmemh("expected.hex",expected);
   $readmemh("controls.hex",routes);
   for(e=0;e<{count+25};e=e+1) begin
     idata=0; controls=0;
     if(e<{count}) idata=inputs[e];
     if(mut_data && e==0) idata[0]=~idata[0];
     for(s=0;s<13;s=s+1) begin
       k=e-2*s;
       if(k>=0 && k<{count}) controls[s*64+:64]=routes[k][s*64+:64];
     end
     if(mut_control && e==12) controls[6*64+31]=~controls[6*64+31];
     #5;ck=1;#1;
     if(e>=25) begin
       if(odata !== expected[e-25])
         $fatal(1,"EXACT_MISMATCH edge%0d frame%0d",e,e-25);
       checked=checked+1;
     end
     #4;ck=0;
   end
   if(checked!={count}) $fatal(1,"wrong comparison count");
   $display("PASS frames%0d words%0d first_zeroindexed_edge25 latency26 II1",checked,checked*128);
   $finish;
 end
endmodule
'''
    runs = []
    with tempfile.TemporaryDirectory(prefix='s81-benes-rail-') as temp:
        work = Path(temp)
        (work / 'bench.sv').write_text(tb)
        for name, values, digits in [('input', inputs, 512), ('expected', expected, 512),
                                      ('controls', controls, 208)]:
            (work / f'{name}.hex').write_text(''.join(f'{v:0{digits}x}\n' for v in values))
        build = subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', 'sim',
                                str(RTL), 'bench.sv'], cwd=work, capture_output=True, text=True)
        if build.returncode:
            raise RuntimeError(build.stdout + build.stderr)
        for mode in ('gold', 'MUTANT_CONTROL', 'MUTANT_DATA'):
            result = subprocess.run(['vvp', 'sim'] + ([] if mode == 'gold' else ['+' + mode]),
                                    cwd=work, capture_output=True, text=True)
            output = result.stdout + result.stderr
            passed = result.returncode == 0 and 'PASS frames104 words13312' in output
            rejected = result.returncode != 0 and 'EXACT_MISMATCH' in output
            if not (passed if mode == 'gold' else rejected):
                raise RuntimeError(f'{mode} unexpected result {result.returncode}: {output}')
            runs.append(dict(mode=mode, returncode=result.returncode, output=output.strip(),
                             exact_pass=passed, mutant_rejected=rejected))
    evidence = dict(status='PASS_ISOLATED_FULL128_W16_RTL_ONLY_NOT_PHYSICALLY_QUALIFIED',
                    source_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                                   [RTL, Path(__file__), ROOT / 'tools/s81_vm/area_benes_routes.py']},
                    generated_bench_sha256=hashlib.sha256(tb.encode()).hexdigest(),
                    topology=dict(sources=128, data_width=16, stages=13, switches_per_stage=64,
                                  clock_pins=13, clocks='functionally tied for this bench only',
                                  pin_registers_per_stage=2112, output_registers_per_stage=2048,
                                  total_flops_per_stage_root=4160, hidden_parent_delay_flops=0),
                    latency=dict(physical_edges=26, first_output_zeroindexed_edge=25,
                                 II=1, control_calendar='stage s gets frame e-2*s at sampling edge e',
                                 scope='network only; parent compiler schedules controls externally'),
                    frames=count, first_four_frames_live_sources=53,
                    first_four_frames_bank_lane_destinations=96, random_full128_permutations=100,
                    exact_words_compared=count * 128,
                    payload='valid[15], frame_tag[14:7], source_identity[6:0]; padding invalid and distinguishable',
                    reset_scope='no reset contract claimed; startup ignored until first complete frame',
                    runs=runs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(dict(status=evidence['status'], frames=count, words=count*128,
                         mutant_control_rejected=True, mutant_data_rejected=True)))


if __name__ == '__main__':
    main()
