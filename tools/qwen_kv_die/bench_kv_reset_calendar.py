#!/usr/bin/env python3
"""Causal one-bit PLL landing bench with the model's 89 reset relay edges.

Derives the existing pinned full lane bench, adds actual qkd_rlys_1 reset cells,
and tests the recompiled G-R0 strap against stale-calendar and missing-capture
mutants. This is mechanism evidence, not a selected-die/calendar qualification.
Run only through ot-run with Verilator 5.050.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--topology', choices=['pll', 'all'], default='pll')
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    runner = root/'tools/qwen_kv_die/bench_kv_fwd_lane.sh'
    text = runner.read_text()
    bench = text.split('cat > "$O/tb.sv" <<\'EOT\'\n',1)[1].split('\nEOT\n',1)[0]
    changes = [
        ('reg en = 0, rs = 0;', 'reg en_root = 0, rs = 0; wire en;'),
        ('en <= (es >= G);', 'en_root <= (es >= G);'),
        ('(E + H0) % 8;', '(E + ((LM == 6 && NF > 1) ? 0 : H0) + ((LM == 4) ? 0 : 89)) % 8;'),
        ('te_ >= G + H0', 'te_ >= G + 89 + H0'),
        ('ed > G + 20', 'ed > G + 89 + 20'),
        ('#3000;', '#6000;')]
    for before, after in changes:
        if bench.count(before) != 1:
            raise ValueError('pinned bench shape changed: ' + before)
        bench = bench.replace(before,after)
    if a.topology == 'all':
        before = '(NF == 1) ? 1 : 0;'
        if bench.count(before) == 1:
            bench = bench.replace(before,'1; // actual FIRST=1 en capture on every lane')
        elif 'localparam integer H0 = 1;' not in bench:
            raise ValueError('pinned hop-0 expression changed')
    else:
        bench = bench.replace('localparam integer W = 36;', 'localparam integer W = 1;')
        bench = bench.replace('qkd_landsh0_36 u_l','qkd_landsh0_1 u_l')
    # Only the NF=1, one-bit topology matches the concrete worst PLL endpoint.
    # Five distinct release epochs exercise the same source/receiver offset.
    replacements = [
        ('.NF(1),  .LM(`LM)', '.NF(1), .LM(`LM), .G(10)'),
        ('.NF(2),  .LM(`LM)', '.NF(1), .LM(`LM), .G(42)'),
        ('.NF(5),  .LM(`LM)', '.NF(1), .LM(`LM), .G(80)'),
        ('.NF(15), .LM(`LM)', '.NF(1), .LM(`LM), .G(120)'),
        ('.NF(40), .LM(`LM), .CD(0.1)', '.NF(1), .LM(`LM), .G(170)')]
    for before, after in (replacements if a.topology == 'pll' else []):
        if bench.count(before) != 1:
            raise ValueError('pinned topology shape changed: ' + before)
        bench = bench.replace(before,after)
    anchor = '    wire [W-1:0] d [0:NF];'
    chain = '''    localparam integer RESET_DEPTH = (LM == 5) ? 88 : 89;
    wire [RESET_DEPTH:0] reset_chain;
    assign reset_chain[0] = en_root;
    assign en = reset_chain[RESET_DEPTH];
    genvar rz;
    generate for (rz = 0; rz < RESET_DEPTH; rz = rz + 1) begin : g_actual_reset
        qkd_rlys_1 u_rst (.ck(cks), .a(reset_chain[rz]), .b(reset_chain[rz+1]));
    end endgenerate
'''
    if bench.count(anchor) != 1:
        raise ValueError('pinned lane anchor changed')
    bench = bench.replace(anchor,chain+anchor)
    tb = out/'tb.sv'
    tb.write_text(bench+'\n')
    sources = ['rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv',
               'rtl/qwen_split/qfd_fwd_lane.sv', 'rtl/hdc/ot_hdc_cg.sv',
               'rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv']
    hashes = {n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in sources}
    hashes[str(runner.relative_to(root))] = hashlib.sha256(runner.read_bytes()).hexdigest()
    v = os.environ.get('VERILATOR', str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
    version = subprocess.check_output([v,'--version'],text=True)
    if '5.050' not in version:
        raise ValueError('requires pinned Verilator 5.050')
    results = []
    modes = [('calendar',3),('stale_calendar',4),('missing_capture',5)]
    if a.topology == 'all':
        modes.append(('legacy_hop0',6))
    for mode, lm in modes:
        d = out/mode
        d.mkdir(exist_ok=True)
        command = [v,'--binary','--timing','-Wno-fatal','-Wno-WIDTH','-Wno-MULTIDRIVEN',
            '-Wno-COMBDLY','-Wno-LATCH','-Wno-INITIALDLY','--top-module','tb',
            '+define+LM='+str(lm),'-Mdir',str(d/'obj'),'-o','tb',str(tb),*sources]
        with (d/'build.log').open('w') as log:
            subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
        with (d/'bench.log').open('w') as log:
            subprocess.run([str(d/'obj/tb')],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
        output = (d/'bench.log').read_text()
        observed_pass = 'KV_FWD_BENCH PASS' in output
        observed_fail = 'KV_FWD_BENCH FAIL' in output and 'KV_FWD_LANE MISMATCH' in output
        expected = observed_pass if lm == 3 else observed_fail
        result = dict(mode=mode, expected_outcome_observed=expected,
                      summaries=[l for l in output.splitlines() if 'KV_FWD_BENCH' in l])
        results.append(result)
        print(json.dumps(result),flush=True)
    receipt = dict(status='MECHANISM_ONLY_NOT_DIE_QUALIFIED',verilator=version.strip(),
                   source_sha256=hashes,bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest(),
                   source_reset_edges=89, receiver_reset_edges=0,results=results)
    receipt['topology'] = a.topology
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if all(r['expected_outcome_observed'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
