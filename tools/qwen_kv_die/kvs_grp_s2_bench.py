#!/usr/bin/env python3
"""KV-GRP2 2026-10-19: equivalence bench of the safe group tiles qkd_kvs_grp_s2 / qkd_kvs_grp_h_s2.

Oracle = the UNCHANGED sha-pinned DOMSPLIT MU/BOOT_AGES tiles (tb/qkd_kvs_grp_s2_ref.sv: renamed only) on the unchanged
leaves and the unchanged 128x256 macro model.  The bench applies the documented safe2 ages to the oracle's INPUTS only:
i_ctl, i_up, x__est one core edge later (tb flops), rst_n / hrst_n through the same two-stage landing as the tile (tb
model), the four deleted pins (x__tok / x__tep, x__est[12:1]) driven randomly into the oracle and absent from the DUT.
Every retained DUT output is then compared bit-exact with the oracle output at every core AND every HBM falling edge
(independent clocks 834 / 1024 ps, three reset pulses, random two-state stimulus, 6000 core edges, both tiles).
MUT 1..7 (kv_grp_safe2.MUTANTS) must each FAIL with S2_FAIL.

    python3 tools/qwen_kv_die/kvs_grp_s2_bench.py --out DIR [--cases m0,m1,...] [--edges N]   (fleet: Verilator 5.050)
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_grp_safe2 as S2  # noqa: E402

LEAVES = [
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_cfault_tree.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_front_cal.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_landing_cal.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_lvl_land.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_cdc.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_hop.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing_seg.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_ownership.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_phase_launch.sv',
    'rtl/lib/ot_async_fifo.sv',
    'rtl/lib/ot_reset_sync.sv',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
    S2.MACRO_DIR + '/' + S2.MACRO + '.v',
]
SOURCES = [S2.OUT, S2.REF] + LEAVES
DELAYED = ('i_ctl', 'i_up', 'x__est')


def ports(text, name):
    m = re.search(r'^module ' + name + r'\b.*?\((.*?)\n\);', text, re.S | re.M)
    out = []
    for d, w, n in re.findall(r'(input|output) wire (?:\[(\d+):0\] )?(\w+)', m.group(1)):
        out.append((d, int(w) + 1 if w else 1, n))
    return out


def rnd(w):
    return '{' + ','.join(['$random(seed)'] * ((w + 31) // 32)) + '}'


def tb(edges):
    dut_t = (ROOT / S2.OUT).read_text()
    ref_t = (ROOT / S2.REF).read_text()
    L = ['`timescale 1ps/1ps', 'module tb;', 'reg ck = 0, hck = 0;', 'always #417 ck = ~ck;', 'always #512 hck = ~hck;',
         'integer e, checks = 0, mut = 0, seed = 1019;', 'reg rst_n = 0, hrst_n = 0;',
         '// the tile landing, modelled in the bench for the oracle: async assert, release on the 2nd own-clock edge',
         'reg c1 = 0, c2 = 0, h1 = 0, h2 = 0;',
         'always @(posedge ck or negedge rst_n) if (!rst_n) begin c1 <= 0; c2 <= 0; end else begin c1 <= 1; c2 <= c1; end',
         'always @(posedge hck or negedge hrst_n) if (!hrst_n) begin h1 <= 0; h2 <= 0; end else begin h1 <= 1; h2 <= h1; end']
    checks = []
    for name, new in S2.KINDS:
        k = 'g' if name == 'qkd_kvs_grp' else 'h'
        rp, dp = ports(ref_t, name + '_ref'), ports(dut_t, new)
        dnames = {n: (d, w) for d, w, n in dp}
        ref_c, dut_c = [], []
        for d, w, n in rp:
            if n in ('ck', 'hck'):
                ref_c.append(f'.{n}({n})')
                continue
            if n in ('rst_n', 'hrst_n'):
                ref_c.append(f'.{n}({"c2" if n == "rst_n" else "h2"})')
                continue
            if d == 'input':
                L.append(f'reg [{w - 1}:0] {k}_{n} = 0;')
                if n in DELAYED:
                    L.append(f'reg [{w - 1}:0] {k}_{n}_d = 0; always @(posedge ck) {k}_{n}_d <= {k}_{n};')
                    ref_c.append(f'.{n}({k}_{n}_d)')
                else:
                    ref_c.append(f'.{n}({k}_{n})')
            else:
                L.append(f'wire [{w - 1}:0] {k}_r_{n};')
                ref_c.append(f'.{n}({k}_r_{n})')
        for d, w, n in dp:
            if n in ('ck', 'hck', 'rst_n', 'hrst_n'):
                dut_c.append(f'.{n}({n})')
            elif d == 'input':
                rw = next(ww for dd, ww, nn in rp if nn == n)
                dut_c.append(f'.{n}({k}_{n}[{w - 1}:0])' if rw != w else f'.{n}({k}_{n})')
            else:
                L.append(f'wire [{w - 1}:0] {k}_d_{n};')
                dut_c.append(f'.{n}({k}_d_{n})')
                rw = next(ww for dd, ww, nn in rp if nn == n)
                checks.append((k, n, w, rw))
        L.append(f'{name}_ref ref_{k} ({", ".join(ref_c)});')
        L.append(f'{new} #(.MUT(MUT)) dut_{k} ({", ".join(dut_c)});')
        stim = []
        for d, w, n in rp:
            if d == 'input' and n not in ('ck', 'hck', 'rst_n', 'hrst_n'):
                stim.append(f'  {k}_{n} = {rnd(w)};')
        # sparse strobes (1/8): boot cfg we / last, landing cfg we, phase go, kgo, vgo -> long legal-looking stretches
        for b in (174, 181, 182) + tuple(range(183, 194)):
            stim.append(f'  {k}_i_ctl[{b}] = $random(seed) & $random(seed) & $random(seed);')
        L.append(f'task stim_{k}; begin')
        L += stim
        L.append('end endtask')
    L.append('task compare(input integer side); begin')
    for k, n, w, rw in checks:
        sl = f'[{w - 1}:0]' if rw != w else ''
        L.append(f'  checks = checks + 1; if ({k}_d_{n} !== {k}_r_{n}{sl}) begin '
                 f'$display("S2_FAIL tile=%s output={n} edge=%0d side=%0d mut=%0d dut=%h ref=%h", "{k}", e, side, mut, '
                 f'{k}_d_{n}, {k}_r_{n}{sl}); $fatal(1); end')
    L.append('end endtask')
    L.append('always @(negedge hck) if (e > 0) compare(1);')
    L.append('initial begin')
    L.append('  if (!$value$plusargs("mut=%d", mut)) mut = MUT;')
    L.append(f'  for (e = 0; e < {edges}; e = e + 1) begin')
    L.append('    @(negedge ck);')
    L.append('    compare(0);')
    L.append('    rst_n = !(e < 6 || (e >= 2500 && e < 2507) || (e >= 4100 && e < 4103));')
    L.append('    hrst_n = !(e < 7 || (e >= 2501 && e < 2509) || (e >= 4100 && e < 4104));')
    L.append('    stim_g; stim_h;')
    L.append('  end')
    L.append(f'  $display("S2_PASS checks=%0d edges={edges} mut=%0d", checks, mut); $finish;')
    L.append('end')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--cases', default=','.join(f'm{i}' for i in [0] + sorted(S2.MUTANTS)))
    ap.add_argument('--edges', type=int, default=6000)
    ap.add_argument('--verilator', default=str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
    ap.add_argument('--tb-only', action='store_true')
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    S2.build()                                    # source identity (refuses on drift)
    if subprocess.run([sys.executable, str(ROOT / 'tools/qwen_kv_die/kv_grp_safe2.py'), '--check'],
                      cwd=ROOT).returncode:
        raise SystemExit('generated tile stale')
    results = []
    for case in a.cases.split(','):
        m = int(case[1:])
        txt = tb(a.edges).replace('module tb;', f'module tb;\nlocalparam integer MUT = {m};', 1)
        (out / f'tb_{case}.sv').write_text(txt)
        if a.tb_only:
            continue
        ver = subprocess.check_output([a.verilator, '--version'], text=True).strip()
        cmd = [a.verilator, '--binary', '--timing', '-j', '8', '-Wno-fatal', '-Wno-lint', '-Wno-style', '--x-assign', '0',
               '--x-initial', '0', '--top-module', 'tb', '--Mdir', str(out / f'build_{case}'), str(out / f'tb_{case}.sv')] + \
              [str(ROOT / s) for s in SOURCES]
        with open(out / f'{case}.build.log', 'w') as lg:
            rc = subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT).returncode
        if rc:
            results.append(dict(case=case, verdict='BUILD_FAIL', rc=rc))
            print(json.dumps(results[-1]), flush=True)
            continue
        with open(out / f'{case}.log', 'w') as lg:
            rc = subprocess.run([str(out / f'build_{case}' / 'Vtb')], stdout=lg, stderr=subprocess.STDOUT).returncode
        log = (out / f'{case}.log').read_text()
        if m == 0:
            ok = rc == 0 and 'S2_PASS' in log
        else:
            ok = rc != 0 and 'S2_FAIL' in log
        line = next((ln for ln in log.splitlines() if 'S2_' in ln), '')
        results.append(dict(case=case, mut=m, what=S2.MUTANTS.get(m, 'positive'), rc=rc,
                            verdict=('PASS' if m == 0 else 'FAIL (expected)') if ok else 'UNEXPECTED',
                            witness=line[:400], verilator=ver))
        print(json.dumps(results[-1]), flush=True)
        __import__('shutil').rmtree(out / f'build_{case}', ignore_errors=True)
    src = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES}
    (out / 'results.json').write_text(json.dumps(dict(edges=a.edges, sources=src, cases=results), indent=1) + '\n')
    bad = [r for r in results if r.get('verdict') in ('UNEXPECTED', 'BUILD_FAIL')]
    print('S2_BENCH', 'ALL_OK' if not bad else f'BAD {bad}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
