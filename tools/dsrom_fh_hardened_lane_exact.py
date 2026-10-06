#!/usr/bin/env python3
"""Run the existing full-depth SRAM check on original and reusable-lane RTL.

The original source and bench are never modified. The generated bench also
checks every lane's stored row-nine codeword against the pinned ECC fixture,
so a consistently incorrect bank strap cannot pass by encoding and decoding
with the same incorrect identity. No timeout is imposed on simulation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
old = Path('rtl/hdc/v41/dspark_fused_head/capture_candidate')
new = Path('rtl/hdc/v41/dspark_fused_head/lane_hardened')
paths = [Path('rtl/dft/ot_rom_secded_dec.sv'),
         old / 'ot_hdc_v41_fh_sram_return.sv',
         new / 'ot_hdc_v41_fh_sram_return_hardened.sv',
         Path('physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v')]
bench = (ROOT / old / 'tb_fh_sram_return.sv').read_text()
bench = bench.replace('wire fault;', 'wire fault;\n    wire [3:0] address_fault_bits;\n    wire [64*55-1:0] observed_codeword;\n    for(genvar probe=0;probe<64;probe=probe+1) begin : g_probe\n        assign observed_codeword[55*probe+:55]=dut.g_bank[probe].u_lane.raw_word_r;\n    end')
needle = 'idle(8);check_stream=1;'
assert bench.count(needle) == 1
bench = bench.replace(needle, 'idle(8);\n        // Observe actual stored native bank identities, not a second encoder.\n        read_round(9);idle(8);accepted=0;released=0;\n        for(b=0;b<64;b=b+1) if(observed_codeword[55*b+:55]!==gold_ecc[b])\n            $fatal(1,"stored canonical identity lane%0d",b);\n        check_stream=1;')
results = []
for name in ('original', 'hardened', 'wrong_bank_negative'):
    d = a.output / name
    d.mkdir()
    body = bench
    if name != 'original':
        body = body.replace('ot_hdc_v41_fh_sram_return #(',
                            'ot_hdc_v41_fh_sram_return_hardened #(')
    sources = [ROOT / x for x in paths]
    if name == 'wrong_bank_negative':
        mutated = (ROOT / paths[2]).read_text().replace(".bank_id(6'(b))", ".bank_id(6'(b)^6'd1)")
        assert mutated != (ROOT / paths[2]).read_text()
        mutant = d / 'wrong_bank.sv'
        mutant.write_text(mutated)
        sources[2] = mutant
    tb = d / 'tb.sv'
    tb.write_text(body)
    exe = d / 'sim.vvp'
    cmd = ['iverilog', '-g2012', '-DOT_FH_PROTECT_SPLIT=1', '-s', 'tb_fh_sram_return',
           '-o', str(exe), *map(str, sources), str(tb)]
    with (d / 'compile.log').open('w') as log:
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
    if rc:
        raise SystemExit(f'{name} compile failed rc={rc}: {d / "compile.log"}')
    run = subprocess.run(['vvp', str(exe), '+ECC=' + str(ROOT / old / 'ecc_K48_row9.hex')],
                         text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (d / 'run.log').write_text(run.stdout)
    lines = [x for x in run.stdout.splitlines() if x.startswith('PASS FH SRAM')]
    if name == 'wrong_bank_negative':
        passed = run.returncode != 0 and 'stored canonical identity' in run.stdout
    else:
        passed = run.returncode == 0 and len(lines) == 1
    results.append(dict(configuration=name, returncode=run.returncode, passed=passed,
                        checks=lines, compile_argv=cmd))
    if not passed:
        raise SystemExit(f'{name} failed: {d / "run.log"}')
assert results[0]['checks'] == results[1]['checks'], 'Trace accounting changed'
record = dict(passed=True, added_cycles=0, cases=results,
              sha256={str(x): hashlib.sha256((ROOT/x).read_bytes()).hexdigest()
                      for x in paths + [old/'tb_fh_sram_return.sv', old/'ecc_K48_row9.hex']})
(a.output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
print('PASS reusable SRAM lane: full G4W16 rows505, per-cycle validity/payload, canonical bank identity, warm masks, SECDED/foreign-bank negatives; wrong-bank mutant rejected; +0 cycles')
