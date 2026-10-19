#!/usr/bin/env python3
"""KV-PC 2026-10-19: lockstep bench of the PC kit tiles qkd_kvs_pc / qkd_kvs_pc_h after the safe-design fixes:
  DUT = the committed OT_KV_PC_RLAND tile (qkd_kvs_tiles_hroot_ff_k_mu_ds_rl.sv: rst_n landed on ck, hrst_n on hck, 2
        stages each, ot_reset_sync) with the current qkd_static_kv_pc_path_fan_nc_b (KEPT strap pin registers pc_sr /
        st_sr in front of u_pce);
  REF = the committed un-landed tile (qkd_kvs_tiles_hroot_ff_k_mu_ds.sv) with the PRE-CHANGE fan_nc_b (strap pins
        straight into u_pce; rtl/test/qwen_static_kv/kvpc_rland/qkd_static_kv_pc_path_fan_nc_b_ref.sv), its resets
        landed OUTSIDE the tile by the same 2-stage ot_reset_sync per domain.
Claim: the landing + strap registers change nothing but the reset release point (+2 edges per domain, the same as an
external landing), i.e. every tile output is equal every ck and hck edge.  Two clocks: ck 834 ps, hck 1024 ps
(offset 0.3 ps: no coincident edges).  Resets low 12 ck edges; random inputs on every ck edge from the release on (the
landing window is exercised), straps constant.
--mut (must FAIL): 1 hck landing clocked by ck; 2 u_pc.cal_rst_n left on the raw hrst_n; 3 u_embr on the raw rst_n;
4 fan_nc_b strap register feeds u_pce a swapped cfg_stack; 5 fan_nc_b strap register feeds u_pce pc ^ 1.
    python3 tools/qwen_kv_die/kvs_pc_rland_bench.py --tile pc|pc_h [--mut N] [--edges 3000] --out DIR
One line 'KVPC_RLAND PASS|FAIL tile=<t> ...'; exit 0 only on PASS.  Verilator: the closure daemon's 5.050 on PATH."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
D = 'rtl/qwen_sys/static_kv_die_20261017/'
DUT_FILE = D + 'qkd_kvs_tiles_hroot_ff_k_mu_ds_rl.sv'
REF_FILE = D + 'qkd_kvs_tiles_hroot_ff_k_mu_ds.sv'
FAN = 'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv'
FAN_REF = 'rtl/test/qwen_static_kv/kvpc_rland/qkd_static_kv_pc_path_fan_nc_b_ref.sv'
KIT = dict(pc='physical/ref_tile/qkd_kvs_pc_rl1/spec.json', pc_h='physical/ref_tile/qkd_kvs_pc_h_rl1/spec.json')
STRAP = dict(pc__pc="5'd9", pc__cfg_stack="2'd2")


def module(path, name):
    t = (ROOT / path).read_text()
    m = re.search(rf'^module {name} \(', t, re.M)
    return t[m.start():t.index('endmodule\n', m.start()) + len('endmodule\n')]


def ports(txt):
    hdr = txt[:txt.index(');')]
    out = []
    for d, w, n in re.findall(r'^\s*(input|output) wire (?:\[(\d+):0\] )?(\w+)', hdr, re.M):
        out.append((n, d, int(w) + 1 if w else 1))
    return out


def mutate_dut(t, mut):
    if mut == 1:
        n = t.replace('u_rland_hck (.clk(hck)', 'u_rland_hck (.clk(ck)')
    elif mut == 2:
        n = t.replace('.cal_rst_n(w_rland__hrst_n)', '.cal_rst_n(hrst_n)')
    elif mut == 3:
        n = re.sub(r'(u_embr \(\.ck\(ck\), \.rst_n\()w_rland__rst_n\)', r'\1rst_n)', t)
    else:
        return t
    if n == t:
        raise SystemExit(f'kvs_pc_rland_bench: mutant {mut} found no site')
    return n


def mutate_fan(t, mut):
    a = t.index('module qkd_static_kv_pc_path_fan_nc_b')
    j = t.index('u_pce (', a)
    if mut == 4:
        n = t[:j] + t[j:].replace('.cfg_stack(st_sr),', '.cfg_stack({st_sr[0], st_sr[1]}),', 1)
    elif mut == 5:
        n = t[:j] + t[j:].replace('.pc(pc_sr),', '.pc(pc_sr ^ 5\'d1),', 1)
    else:
        return t
    if n == t:
        raise SystemExit(f'kvs_pc_rland_bench: mutant {mut} found no site')
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tile', required=True, choices=('pc', 'pc_h'))
    ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--edges', type=int, default=3000)
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=8)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    nm = f'qkd_kvs_{a.tile}'
    dut = mutate_dut(module(DUT_FILE, nm), a.mut)
    ref = module(REF_FILE, nm)
    if 'u_rland_ck' not in dut or 'u_rland' in ref:
        raise SystemExit('kvs_pc_rland_bench: DUT must be the landed tile, REF the un-landed one')
    ref = ref.replace(f'module {nm} (', 'module ref_tile (', 1).replace(
        'qkd_static_kv_pc_path_fan_nc_b #(', 'qkd_static_kv_pc_path_fan_nc_b_ref #(', 1)
    if 'qkd_static_kv_pc_path_fan_nc_b_ref' not in ref:
        raise SystemExit('kvs_pc_rland_bench: REF tile has no fan_nc_b instance')
    dut = dut.replace(f'module {nm} (', 'module dut_tile (', 1)
    (out / 'tiles.sv').write_text('`timescale 1ps/1fs\n' + ref + '\n' + dut)
    fan = mutate_fan((ROOT / FAN).read_text(), a.mut)
    (out / 'fan_nc_b.sv').write_text(fan)
    P = ports(dut)
    if P != ports(ref.replace('module ref_tile (', f'module {nm} (')):
        raise SystemExit('kvs_pc_rland_bench: DUT and REF ports differ')
    clk = {'ck', 'hck'}
    rst = {'rst_n', 'hrst_n'}
    ins = [(n, w) for n, d, w in P if d == 'input' and n not in clk | rst]
    outs = [(n, w) for n, d, w in P if d == 'output']
    rnd = lambda w: '{' + ', '.join(['$random'] * ((w + 31) // 32)) + '}'     # noqa: E731
    L = ['`timescale 1ps/1fs', 'module tb_kvpc_rland;',
         '  reg ck = 0; always #417 ck = ~ck;',
         '  reg hck = 0; initial begin #0.3; forever #512 hck = ~hck; end',
         '  reg rst_n = 0, hrst_n = 0;', '  wire ref_rst_n, ref_hrst_n;',
         '  ot_reset_sync #(.ASYNC_STAGES(2)) u_lr_ck (.clk(ck), .async_rst_n(rst_n), .sync_rst_n(ref_rst_n));',
         '  ot_reset_sync #(.ASYNC_STAGES(2)) u_lr_hck (.clk(hck), .async_rst_n(hrst_n), .sync_rst_n(ref_hrst_n));',
         '  integer t, bad, chk, act;']
    for n, w in ins:
        L.append(f'  reg [{w - 1}:0] {n};')
    for n, w in outs:
        L.append(f'  wire [{w - 1}:0] r__{n}, d__{n};')
    rmap = dict(rst_n='ref_rst_n', hrst_n='ref_hrst_n')
    L.append('  ref_tile u_ref (' + ', '.join(f'.{n}({rmap.get(n, "r__" + n if d == "output" else n)})'
                                             for n, d, w in P) + ');')
    L.append('  dut_tile u_dut (' + ', '.join(f'.{n}({"d__" + n if d == "output" else n})' for n, d, w in P) + ');')
    cmp_ = []
    for n, w in outs:
        cmp_.append(f'      chk = chk + 1; if (r__{n} !== d__{n}) begin bad = bad + 1; '
                    f'if (bad < 8) $display("MISMATCH t=%0d %s out {n}", t, phase); end')
    L.append('  reg [8*3-1:0] phase;')
    L.append('  task compare; begin')
    L += cmp_
    L.append('  end endtask')
    L.append('  always @(negedge hck) if (rst_n) begin phase = "hck"; compare; end')
    L.append('  initial begin')
    L.append('    bad = 0; chk = 0; act = 0;')
    for n, w in ins:
        L.append(f'    {n} = {STRAP.get(n, "0")};')
    L.append('    repeat (12) @(negedge ck);')
    L.append('    rst_n = 1; hrst_n = 1;')
    L.append(f'    for (t = 0; t < {a.edges}; t = t + 1) begin')
    L.append('      @(negedge ck); phase = "ck";')
    L.append('      compare;')
    for n, w in outs:
        L.append(f'      if (d__{n} != 0) act = act + 1;')
    for n, w in ins:
        if n not in STRAP:
            L.append(f'      {n} = {rnd(w)};')
    L.append('    end')
    L.append(f'    if (bad == 0 && act > 0) $display("KVPC_RLAND PASS tile={a.tile} edges={a.edges} checks=%0d '
             f'active_out=%0d outs={len(outs)} errors=0 mut={a.mut} vs=ref_unlanded_external_landing", chk, act);')
    L.append(f'    else $display("KVPC_RLAND FAIL tile={a.tile} edges={a.edges} checks=%0d errors=%0d active_out=%0d '
             f'mut={a.mut}", chk, bad, act);')
    L.append('    $finish;')
    L.append('  end')
    L.append('endmodule')
    (out / 'tb.sv').write_text('\n'.join(L) + '\n')
    sp = json.loads((ROOT / KIT[a.tile]).read_text())
    srcs = [s for s in sp['sources'] if s not in (DUT_FILE, FAN)] + [FAN_REF]
    dirs = sorted({str(Path(s).parent) for s in srcs} | {'rtl/lib'})
    cmd = ['verilator', '--binary', '--timing', '-j', str(a.threads), '-Wno-fatal', '-Wno-lint', '-Wno-style',
           '-Wno-TIMESCALEMOD', '--top-module', 'tb_kvpc_rland', '-Mdir', str(out / 'obj'), '-o', 'sim',
           str(out / 'tb.sv'), str(out / 'tiles.sv'), str(out / 'fan_nc_b.sv')] + srcs + ['+libext+.sv+.v'] + \
        [x for d in dirs for x in ('-y', d)]
    print('SIM ' + subprocess.run(['verilator', '--version'], capture_output=True, text=True).stdout.strip())
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        print(f'KVPC_RLAND FAIL tile={a.tile} build mut={a.mut}')
        return 2
    r = subprocess.run([str(out / 'obj' / 'sim')], capture_output=True, text=True, cwd=ROOT)
    print(r.stdout[-4000:])
    line = [ln for ln in r.stdout.splitlines() if ln.startswith('KVPC_RLAND ')]
    if not line:
        print(f'KVPC_RLAND FAIL tile={a.tile} no verdict mut={a.mut}')
        return 1
    return 0 if line[-1].startswith('KVPC_RLAND PASS') else 1


if __name__ == '__main__':
    sys.exit(main())
