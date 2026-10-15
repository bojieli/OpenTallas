#!/usr/bin/env python3
"""Native synchronous-reset compact-ID quarter and startup gate."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
OUT = ROOT / 'results/arch/s81_vm_area_1417/native_id_proof.json'
SOURCES = ['tools/s81_vm/area_id_native.sv', 'tools/s81_vm/area_id_native_gate.py',
           'tools/s81_vm/area_stripe_bench.sv'] + [
               f'rtl/dsrom_sys/s81_ph/vm/{name}.sv' for name in
               ['dsfd_vm_static_wdispatch128', 'dsfd_vm_static_wstage128',
                'dsfd_vm_static_write_capture128']]


def check_lock():
    if json.loads(LOCK.read_text())['owner'] != 'codex':
        raise RuntimeError('coordinator ownership changed')


def run(cmd):
    check_lock()
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    check_lock()
    return result


def startup_gate():
    bench = '''`timescale 1ns/1ps
module startup;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;
 reg [52:0] v=53'b1<<52;
 reg [741:0] row=0;reg [105:0] lane=0;
 reg [211:0] mask=0;reg [423:0] tag=0;reg [6783:0] data=0;
 reg [7:0] dv=0;reg [15:0] ds=0;
 wire [7:0] ov;wire [111:0] ore;wire [31:0] om;
 wire [63:0] ot;wire [1023:0] od;wire fault;
 s81_area_quarter dut(ck,ck,{8{ck}},rst,v,row,lane,mask,tag,data,dv,ds,ov,ore,om,ot,od,fault);
 task tick;begin @(posedge ck);#1;end endtask
 task clear_check;begin
   if(fault!==0 || ov!==0 || dut.u_sel.o_sel!==0)
     $fatal(1,"NATIVE_RESET_CHECK failed time%0t",$time);
 end endtask
 initial begin
   lane[104+:2]=3;
   // Initial unknown plain-pin state is allowed until held reset settles.
   repeat(4)tick();clear_check();repeat(2)begin tick();clear_check();end
   @(negedge ck);rst=1;lane[104+:2]=0;
   // Sentinel valid before release and at all three release sampling edges.
   repeat(3)begin tick();clear_check();end
   @(negedge ck);v=0;
   repeat(8)begin tick();clear_check();end
   // Reassertion is synchronous and propagates through the root pin stage.
   @(negedge ck);rst=0;v=53'b1<<52;lane[104+:2]=3;
   repeat(4)tick();clear_check();repeat(2)begin tick();clear_check();end
   @(negedge ck);rst=1;v=0;lane=0;
   repeat(4)begin tick();clear_check();end
   @(negedge ck);v=53'b1<<52;mask[208+:4]=4'ha;tag[416+:8]=8'h5a;
   data[6656+:128]=128'h123456789abcdef00fedcba987654321;
   tick(); // E0 normal source sample
   @(negedge ck);v=0;
   repeat(3)tick(); // E1,E2,E3
   @(negedge ck);dv=1;ds=0;
   tick(); // E4 drain descriptor
   @(negedge ck);dv=0;
   tick(); // E5 registered drain
   if(ov!==1 || fault!==0 || ore[13:0]!==0 || om[3:0]!==4'ha || ot[7:0]!==8'h5a ||
      od[127:0]!==128'h123456789abcdef00fedcba987654321)
     $fatal(1,"NATIVE_NORMAL_RECORD failed");
   $display("PASS native held_reset startup3edges source52 E5 record");$finish;
 end
endmodule
'''
    records = []
    with tempfile.TemporaryDirectory(prefix='s81-native-startup-') as temporary:
        source = Path(temporary) / 'startup.sv'
        check_lock()
        source.write_text(bench)
        for mode, define in [('gold', None), ('held_reset_bypass', 'S81_ID_MUT_HELD_RESET'),
                             ('release_bypass', 'S81_ID_MUT_RELEASE')]:
            executable = str(Path(temporary) / (mode + '.vvp'))
            cmd = ['iverilog', '-g2012', '-s', 'startup', '-o', executable]
            if define:
                cmd.append('-D' + define)
            build = run(cmd + [SOURCES[0], str(source)])
            if build.returncode:
                raise RuntimeError(build.stdout + build.stderr)
            result = run(['vvp', executable])
            passed = result.returncode == 0 and 'PASS native' in result.stdout
            rejected = result.returncode != 0 and 'NATIVE_RESET_CHECK' in result.stdout
            if not (passed if mode == 'gold' else rejected):
                raise RuntimeError(f'{mode}: {result.stdout}{result.stderr}')
            records.append(dict(mode=mode, returncode=result.returncode, stdout=result.stdout,
                                stderr=result.stderr, exact_pass=passed, mutant_rejected=rejected,
                                bench_sha256=hashlib.sha256(bench.encode()).hexdigest()))
    return records


def main():
    records = []
    original = (ROOT / SOURCES[2]).read_text()
    bench = original.replace('@(negedge ck);rst=0;#1;if(fault ||ov)', '@(negedge ck);rst=0;repeat(4)tick();if(fault ||ov)')
    if bench == original:
        raise RuntimeError('reset check insertion changed')
    with tempfile.TemporaryDirectory(prefix='s81-idstripe-') as temporary:
        check_lock()
        (Path(temporary) / 'bench.sv').write_text(bench)
        for base in (0, 8, 16, 24):
            for variant, define in [('gold', None), ('selector', 'S81_AREA_MUT_SELECTOR'),
                                    ('data', 'S81_AREA_MUT_DATA')]:
                executable = str(Path(temporary) / f'b{base}_{variant}.vvp')
                cmd = ['iverilog', '-g2012', '-s', 'tb', f'-Ptb.BASE={base}', '-o', executable]
                if define:
                    cmd.append('-D' + define)
                cmd += [SOURCES[0], str(Path(temporary) / 'bench.sv')] + SOURCES[3:]
                build = run(cmd)
                if build.returncode:
                    raise RuntimeError(build.stdout + build.stderr)
                for mode in (range(5) if variant == 'gold' else (0,)):
                    result = run(['vvp', executable, f'+mode={mode}'])
                    passed = result.returncode == 0 and 'PASS full53sources' in result.stdout
                    rejected = result.returncode != 0 and 'FATAL:' in result.stdout
                    if not (passed if variant == 'gold' else rejected):
                        raise RuntimeError(f'{base}/{variant}/{mode}: {result.stdout}{result.stderr}')
                    records.append(dict(base=base, variant=variant, mode=mode,
                                        exit_code=result.returncode, stdout=result.stdout,
                                        stderr=result.stderr, gold_pass=passed,
                                        mutant_rejected=rejected))
                    print(f'BASE={base} variant={variant} mode={mode} exit={result.returncode}', flush=True)
    startup_records = startup_gate()
    proof = dict(status='PASS_ISOLATED_NATIVE_ID_FULL53_QUARTER_NOT_PRODUCTION_OR_PHYSICALLY_QUALIFIED',
                 reset_scope='raw reset to plain pin flop only, two synchronous release flops, all status synchronous reset; +3FF/root',
                 oldgold_bench_adaptation='temporary copy final raw reset assertion waits4edges instead of async#1; 20case bodies and 3edge startup warmup unchanged',
                 temporary_gold_bench_sha256=hashlib.sha256(bench.encode()).hexdigest(),
                 startup_records=startup_records,
                 selector=dict(records=24, bits_per_record=7, total_bits=168,
                               encoding='valid bit6, sourceID bits5:0; source indices0..52'),
                 model='8 W16 data stripes + W26 metadata stripe + shared registered compact-ID selector',
                 timing='unchanged E0 source -> E1 select -> E2 stripe pin -> E3 mux -> E4 slot -> E5+lane drain; II1',
                 clock_scope='separate leaf pins, functionally tied by unchanged bench; no physical clock-delivery proof',
                 exactness_scope='legal payloads exactly match existing old-quarter gold; invalid schedules prove sticky fault only',
                 duplicate_scope='highest sourceID wins; legacy bitwise-OR duplicate payload is intentionally not represented',
                 checks=dict(gold_cases=20, mutants_rejected=8, bases=[0, 8, 16, 24],
                             modes=['three_slot_burst', 'duplicate', 'invalid_lane', 'empty_drain', 'sustained_II1_lane0'],
                             sources=53, banks_per_quarter=8, slots_per_bank=3,
                             full_row_mask_tag_data=True, reset_clears_fault_and_valid=True),
                 sources={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES},
                 records=records)
    check_lock()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    check_lock()
    OUT.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(dict(status=proof['status'], gold_cases=20, mutants_rejected=8)))


if __name__ == '__main__':
    main()



