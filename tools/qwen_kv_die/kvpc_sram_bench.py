#!/usr/bin/env python3
"""KV-PC 2026-10-19 SAFE redesign benches (Verilator; the closure daemon's 5.050 on PATH).  Each unit runs the ORIGINAL
(flop-array) design and the SRAM-backed successor in lockstep and compares every output every edge.

  front  qkd_kv_hbm_elastic_front_mc_nc  vs qkd_kvpc_s_front         legal block traffic, holds, mid reset
  return qkd_static_kv_return_slots_mc_nc vs qkd_kvpc_s_return       two clocks, legal ring traffic + fault phases
  cdc    ot_qkd_static_emb_cdc            vs ot_qkd_static_emb_cdc_kvpc_s   two clocks, overruns, domain resets
  tq     flop array tq[tr] / tq[tr+1]     vs qkd_kvpc_s_tq            random writes incl. same-edge bypass
  sched  qkd_ctrl_pc_sched_nc             vs qkd_kvpc_s_sched         production parameters, random inputs
  tile   qkd_kvs_pc[_h] (_ds_rl)          vs the OT_KV_PC_SRAM tile (_ds_rl_sr), random inputs, storage roots = hck
Mutants (--mut N, must FAIL): front 1 read +1 / 4 bank permutation / 5 no prefetch; return 1 bank perm / 2 no prefetch;
cdc 1 down bank perm / 2 down no prefetch; tq 1 bypass dropped; sched 1 tag-queue read not advanced
(OT_KVPC_MUT_TQ_NEXT); tile 1 tag-queue read not advanced / 2 front bank permutation / 3 embedding up-FIFO bank permutation inside
the DUT tile (random tile stimulus reaches 3 only: 1 and 2 are covered by their unit benches) / 4 health export drops the
chain fault bit (OT_KVPC_HFX_MUT; KV-PC2: DUT pc__hfx = registered sticky {embr, es_merge, chain} of REF's internal faults).
KV-PC2 10-19: front / return banks write on pll_hbm (no storage-root clocks); unit benches unchanged (roots = pll_hbm).
    python3 tools/qwen_kv_die/kvpc_sram_bench.py --unit U [--tile pc|pc_h] [--mut N] [--edges E] [--seed S] --out DIR
One verdict line 'KVPC_<UNIT> PASS|FAIL ...'; exit 0 only on PASS."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TB = 'rtl/test/qwen_static_kv/kvpc_sram/'
SRAM = 'rtl/qwen_sys/static_kv_20261014/qkd_kvpc_sram_1019.sv'
CLONES = 'rtl/qwen_sys/static_kv_20261014/qkd_kvpc_sram_clones_1019.sv'
MACRO = 'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v'
D = 'rtl/qwen_sys/static_kv_die_20261017/'
REF_TILE = D + 'qkd_kvs_tiles_hroot_ff_k_mu_ds_rl.sv'
DUT_TILE = D + 'qkd_kvs_tiles_hroot_ff_k_mu_ds_rl_sr.sv'
KIT = dict(pc='physical/ref_tile/qkd_kvs_pc_rl1/spec.json', pc_h='physical/ref_tile/qkd_kvs_pc_h_rl1/spec.json')
SCHED_PARAMS = ('.ROW0(64), .CVL(2), .HOFF(3), .WDONE(17), .LATE(4096), .PROFILE(0), .EVMUT(0), .MUT(0), .ELASTIC(1), '
                '.RAW_WD(256), .TQD(64)')
STRAP = dict(pc__pc="5'd9", pc__cfg_stack="2'd2", pc="5'd9", cfg_stack="2'd2")
CTRL_PARAMS = ('.ROW0(64), .CVL(2), .HOFF(3), .WDONE(17), .LATE(4096), .PROFILE(0), .EVMUT(0), .MUT(0), .ELASTIC(1), '
               '.RAW_WD(256), .TQD(64)')


def kit_sources(tile='pc'):
    sp = json.loads((ROOT / KIT[tile]).read_text())
    return [s for s in sp['sources'] if not s.startswith('physical/') and s != REF_TILE]


def module(path, name):
    t = (ROOT / path).read_text()
    m = re.search(rf'^module {name}\b', t, re.M)
    return t[m.start():t.index('endmodule', m.start()) + len('endmodule')] + '\n'


def strip_comments(s):
    return re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', s, flags=re.S))


def ports(txt):
    """[(name, dir, width)] of an ANSI module header (multi-name declarations, parameter header skipped)"""
    t = strip_comments(txt)
    m = re.search(r'\)\s*\(', t) if re.match(r'\s*module\s+\w+\s*#', t) else re.search(r'\(', t)
    depth, i = 1, m.end()
    j = i
    while depth:
        c = t[j]
        depth += (c == '(') - (c == ')')
        j += 1
    out, cur = [], None
    for item in t[i:j - 1].split(','):
        item = ' '.join(item.split())
        if not item:
            continue
        mm = re.match(r'(input|output)\s+(?:wire|reg)?\s*(?:\[(\d+):0\])?\s*(\w+)$', item)
        if mm:
            cur = (mm.group(1), int(mm.group(2)) + 1 if mm.group(2) else 1)
            out.append((mm.group(3), cur[0], cur[1]))
            continue
        mm = re.match(r'(\w+)$', item)
        if mm and cur:
            out.append((mm.group(1), cur[0], cur[1]))
            continue
        raise SystemExit(f'kvpc_sram_bench: cannot parse port item {item!r}')
    return out


def rnd(w):
    return '{' + ', '.join(['$urandom'] * ((w + 31) // 32)) + '}'


def lockstep_tb(name, P, ref_inst, dut_inst, clocks, resets, edges, mut, extra_in=None, tag='SCHED', qual=None,
                strap=None, extra=''):
    """generic two-instance random lockstep: clocks {port: half_period_ps}, resets {port: clock port}; qual {output:
    (valid bit, data msb, data lsb)}: the data slice of that output is compared only while REF's valid bit is set (the
    payload of an EMPTY dual-clock FIFO head: an undefined async read across domains in the original)"""
    extra_in = extra_in or {}
    qual = qual or {}
    straps = STRAP if strap is None else strap
    ins = [(n, w) for n, d, w in P if d == 'input' and n not in clocks and n not in resets and n not in extra_in]
    outs = [(n, w) for n, d, w in P if d == 'output']
    L = ['`timescale 1ps/1fs', f'module {name};']
    first = True
    for c, hp in clocks.items():
        if first:
            L.append(f'  reg {c} = 0; always #{hp} {c} = ~{c};')
            first = False
        else:
            L.append(f'  reg {c} = 0; initial begin #0.3; forever #{hp} {c} = ~{c}; end')
    for r in resets:
        L.append(f'  reg {r} = 0;')
    for n, w in ins:
        L.append(f'  reg [{w - 1}:0] {n};')
    for n, w in outs:
        L.append(f'  wire [{w - 1}:0] r__{n}, d__{n};')
    L.append('  integer t, bad, chk, act, seed, k;')
    L.append('  reg [8*3-1:0] phase;')
    conn = lambda pre: ', '.join(f'.{n}({extra_in.get(n, pre + n if d == "output" else n)})' for n, d, w in P)  # noqa
    L.append(f'  {ref_inst} u_ref ({conn("r__")});')
    L.append(f'  {dut_inst} u_dut ({conn("d__")});')
    L.append('  reg [31:0] nbad [0:%d];' % max(0, len(outs) - 1))
    L.append('  task compare; begin')
    for k, (n, w) in enumerate(outs):
        if n in qual:
            v, hi, lo = qual[n]
            v = f'r__{n}[{v}]' if isinstance(v, int) else v
            parts = ([f"{{{w - hi - 1}{{1'b1}}}}"] if hi < w - 1 else []) + [f"{{{hi - lo + 1}{{{v}}}}}"] + \
                ([f"{{{lo}{{1'b1}}}}"] if lo > 0 else [])
            mask = '{' + ', '.join(parts) + '}'
            cond = f'((r__{n} ^ d__{n}) & {mask}) !== {w}\'d0'
        else:
            cond = f'r__{n} !== d__{n}'
        val = f' %h/%h", t, phase, r__{n}, d__{n});' if w <= 128 else '", t, phase);'
        L.append(f'    chk = chk + 1; if ({cond}) begin bad = bad + 1; nbad[{k}] = nbad[{k}] + 1; '
                 f'if (bad < 8) $display("MISMATCH t=%0d %s out {n}{val} end')
    L.append('  end endtask')
    if extra:
        L.append(extra)
    cks = list(clocks)
    for c in cks:
        L.append(f'  always @(negedge {c}) if ({" && ".join(resets)}) begin phase = "{c[:3]}"; compare; end')
    L.append('  initial begin')
    L.append('    if (!$value$plusargs("seed=%d", seed)) seed = 1; k = $urandom(seed);')
    L.append('    bad = 0; chk = 0; act = 0;')
    L.append(f'    for (k = 0; k < {max(1, len(outs))}; k = k + 1) nbad[k] = 0;')
    for n, w in ins:
        L.append(f'    {n} = {straps.get(n, "0")};')
    L.append(f'    repeat (12) @(negedge {cks[0]});')
    for r in resets:
        L.append(f'    {r} = 1;')
    L.append(f'    for (t = 0; t < {edges}; t = t + 1) begin')
    L.append(f'      @(negedge {cks[0]});')
    for n, w in outs:
        L.append(f'      if (r__{n} != 0) act = act + 1;')
    for n, w in ins:
        if n not in straps:
            L.append(f'      {n} = {rnd(w)};')
    L.append(f'      if (t == {edges // 2}) begin')
    for r in resets:
        L.append(f'        {r} = 0;')
    L.append(f'        repeat (6) @(negedge {cks[0]});')
    for r in resets:
        L.append(f'        {r} = 1;')
    L.append('      end')
    L.append('    end')
    for k, (n, w) in enumerate(outs):
        L.append(f'    if (nbad[{k}] != 0) $display("OUT {n} mismatches=%0d", nbad[{k}]);')
    L.append(f'    if (bad == 0 && act > 0) $display("KVPC_{tag} PASS edges={edges} checks=%0d active_out=%0d '
             f'outs={len(outs)} errors=0 mut={mut}", chk, act);')
    L.append(f'    else $display("KVPC_{tag} FAIL edges={edges} checks=%0d errors=%0d active_out=%0d mut={mut}", '
             'chk, bad, act);')
    L.append('    $finish;')
    L.append('  end')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def build_run(out, top, files, defines, threads, tag, plus=()):
    dirs = sorted({str(Path(s).parent) for s in files if not s.startswith(str(out))} | {'rtl/lib'})
    cmd = ['verilator', '--binary', '--timing', '-j', str(threads), '-Wno-fatal', '-Wno-lint', '-Wno-style',
           '-Wno-TIMESCALEMOD', '-Wno-MULTIDRIVEN', '--top-module', top, '-Mdir', str(out / 'obj'), '-o', 'sim'] + \
        [f'+define+{d}' for d in defines] + [str(f) for f in files] + ['+libext+.sv+.v'] + \
        [x for d in dirs for x in ('-y', d)]
    print('SIM ' + subprocess.run(['verilator', '--version'], capture_output=True, text=True).stdout.strip())
    (out / 'cmd.txt').write_text(' '.join(cmd) + '\n')
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        print(r.stdout[-4000:], r.stderr[-4000:])
        print(f'KVPC_{tag} FAIL build')
        return 2
    r = subprocess.run([str(out / 'obj' / 'sim')] + list(plus), capture_output=True, text=True, cwd=ROOT)
    print(r.stdout[-6000:])
    if r.stderr.strip():
        print(r.stderr[-2000:])
    line = [ln for ln in r.stdout.splitlines() if ln.startswith(f'KVPC_{tag} ')]
    if not line:
        print(f'KVPC_{tag} FAIL no verdict')
        return 1
    return 0 if ' PASS ' in line[-1] else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--unit', required=True, choices=('front', 'return', 'cdc', 'tq', 'sched', 'ctrl', 'path', 'tile'))
    ap.add_argument('--tile', default='pc', choices=('pc', 'pc_h'))
    ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--edges', type=int, default=0)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=8)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    plus = [f'+seed={a.seed}'] + ([f'+edges={a.edges}'] if a.edges else [])
    base = kit_sources(a.tile) + [SRAM, CLONES, MACRO]
    if a.unit in ('front', 'return', 'cdc', 'tq'):
        tag = a.unit.upper()
        tb = TB + f'tb_kvpc_{a.unit}.sv'
        return build_run(out, f'tb_kvpc_{a.unit}', [tb] + base, [f'KVPC_MUT={a.mut}'], a.threads, tag, plus)
    if a.unit == 'sched':
        ref = module('rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv', 'qkd_ctrl_pc_sched_nc')
        dut = module(CLONES, 'qkd_kvpc_s_sched')
        P = ports(ref)
        if P != ports(dut):
            raise SystemExit('kvpc_sram_bench: sched REF / DUT ports differ')
        edges = a.edges or 30000
        tb = lockstep_tb('tb_kvpc_sched', P, f'qkd_ctrl_pc_sched_nc #({SCHED_PARAMS})', f'qkd_kvpc_s_sched #({SCHED_PARAMS})',
                         {'pll_hbm': 512}, {'hrst': 'pll_hbm'}, edges, a.mut, tag='SCHED', strap={})
        (out / 'tb.sv').write_text(tb)
        defs = ['OT_KVPC_MUT_TQ_NEXT'] if a.mut == 1 else []
        return build_run(out, 'tb_kvpc_sched', [str(out / 'tb.sv')] + base, defs, a.threads, 'SCHED', plus)
    if a.unit in ('ctrl', 'path'):
        if a.unit == 'ctrl':
            ref = module('rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv', 'qkd_ctrl_pc_host_static_nc')
            dut = module(CLONES, 'qkd_kvpc_s_ctrl')
            ri, di = f'qkd_ctrl_pc_host_static_nc #({CTRL_PARAMS})', f'qkd_kvpc_s_ctrl #({CTRL_PARAMS})'
            clk = {'ck': 417, 'pll_hbm': 512}
            xin = {k: 'pll_hbm' for k in ('pll_hbm_port', 'pll_hbm_ecc', 'pll_hbm_cdc', 'pll_hbm_obs')}
            rst = {'rsi': 'ck', 'hrst': 'pll_hbm'}
        else:
            ref = module('rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv', 'qkd_static_kv_pc_path_nc')
            dut = module(CLONES, 'qkd_kvpc_s_path_nc')
            ri, di = 'qkd_static_kv_pc_path_nc #(.MU(1))', 'qkd_kvpc_s_path_nc #(.MU(1))'
            clk = {'ck': 417, 'pll_hbm': 512}
            xin = {k: 'pll_hbm' for k in ('pll_hbm_port', 'pll_hbm_ecc', 'pll_hbm_cdc', 'pll_hbm_obs', 'cal_hck',
                                          'front_hck', 'return_hck')}
            xin.update(return_ck='ck', front_hbm_data='{4{pll_hbm}}', return_hbm_data='{4{pll_hbm}}', cal_rst_n='hrst')
            rst = {'rsi': 'ck', 'hrst': 'pll_hbm'}
        P = ports(ref)
        if P != ports(dut):
            raise SystemExit(f'kvpc_sram_bench: {a.unit} REF / DUT ports differ')
        tag = a.unit.upper()
        tb = lockstep_tb(f'tb_kvpc_{a.unit}', P, ri, di, clk, rst, a.edges or 20000, a.mut, extra_in=xin, tag=tag,
                         qual={'er': (0, 258, 1), 'native_commit_identity': ('r__native_commit_valid[0]', 60, 0),
                               'native_commit_address': ('r__native_commit_valid[0]', 28, 0)})
        (out / 'tb.sv').write_text(tb)
        defs = {1: ['OT_KVPC_MUT_TQ_NEXT'], 2: ['OT_KVPC_CDC_UP_MUT'], 3: ['OT_KVPC_FRONT_MUT4']}.get(a.mut, [])
        return build_run(out, f'tb_kvpc_{a.unit}', [str(out / 'tb.sv')] + base, defs, a.threads, tag, plus)
    # tile: DUT = the OT_KV_PC_SRAM tile, REF = the _rl tile; storage roots driven by hck in both
    nm = f'qkd_kvs_{a.tile}'
    ref = module(REF_TILE, nm).replace(f'module {nm} (', 'module ref_tile (', 1)
    dut = module(DUT_TILE, nm).replace(f'module {nm} (', 'module dut_tile (', 1)
    if 'qkd_kvpc_s_fan_nc_b' not in dut or 'qkd_kvpc_s_fan_nc_b' in ref:
        raise SystemExit('kvpc_sram_bench: DUT must be the SRAM tile, REF the _rl tile')
    (out / 'tiles.sv').write_text('`timescale 1ns/1ps\n' + ref + '\n' + dut)
    P = ports(ref)
    if P != [p for p in ports(dut) if p[0] != 'pc__hfx'] or ('pc__hfx', 'output', 3) not in ports(dut):
        raise SystemExit('kvpc_sram_bench: tile REF / DUT ports differ (DUT = REF + output [2:0] pc__hfx)')
    edges = a.edges or 3000
    # KV-PC2 health export: DUT pc__hfx must be the registered sticky OR of REF's three internal faults (which reach no
    # REF port), {u_embr fault, es_merge, chain}, cleared by the landed ck reset.
    hfx = '\n'.join([
        '  reg [2:0] hfx_m; integer hfx_act = 0;',
        '  always @(posedge ck or negedge u_ref.w_rland__rst_n)',
        "    if (!u_ref.w_rland__rst_n) hfx_m <= 3'd0;",
        '    else hfx_m <= hfx_m | {u_ref.w_embr__fault[0], u_ref.w_pc__es_merge_fault[0], u_ref.w_pc__chain_fault[0]};',
        '  always @(negedge ck) if (rst_n && hrst_n) begin chk = chk + 1; if (u_dut.pc__hfx != 0) hfx_act = hfx_act + 1;',
        '    if (u_dut.pc__hfx !== hfx_m) begin bad = bad + 1;',
        '      if (bad < 8) $display("MISMATCH t=%0d out pc__hfx %h/%h", t, hfx_m, u_dut.pc__hfx); end end',
        '  final $display("HFX active_edges=%0d final=%b", hfx_act, hfx_m);'])
    xin = {'pc__front_hbm_data': '{4{hck}}', 'pc__return_hbm_data': '{4{hck}}'}
    tb = lockstep_tb('tb_kvpc_tile', P, 'ref_tile', 'dut_tile', {'ck': 417, 'hck': 512}, {'rst_n': 'ck', 'hrst_n': 'hck'},
                     edges, a.mut, extra_in=xin, tag='TILE', extra=hfx)
    (out / 'tb.sv').write_text(tb)
    files = [str(out / 'tb.sv'), str(out / 'tiles.sv')] + base
    defs = {1: ['OT_KVPC_MUT_TQ_NEXT'], 2: ['OT_KVPC_FRONT_MUT4'], 3: ['OT_KVPC_CDC_UP_MUT'],
            4: ['OT_KVPC_HFX_MUT']}.get(a.mut, [])
    return build_run(out, 'tb_kvpc_tile', files, defs, a.threads, 'TILE', plus)


if __name__ == '__main__':
    sys.exit(main())
