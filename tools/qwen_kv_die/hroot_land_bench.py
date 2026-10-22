#!/usr/bin/env python3
"""HKV-HROOTK2 2026-10-19: latency lockstep of the LANDED stack root tile qkd_kvs_hroot (OT_KV_HROOT_LAND=1: every pin
registered at its face, rtl/qwen_sys/static_kv_die_20261017/qkd_kv_hroot_land.sv) against the UNLANDED tile of the same
design point (OT_KV_HROOT_LAND=0) whose every data input (all but ck / rst_n) is delayed by exactly ONE edge.

Claim checked: the landing adds exactly +1 edge on every word through the root (kv_static_die.HROOT_LAND_EDGES: es chain
head h -> o_pc, fan i_ctl -> o_c*/o_kg/o_ch0, gathers i_g -> o_ctl, return train i_r -> o_emb) and nothing else: every
output equal (!==) every edge after reset, random inputs every edge (resets low for 6 edges).  Both tiles are regenerated
from tools/qwen_kv_die/kv_static_die.py (never read from a stale file).
--mut (applied to the LANDED tile only; must FAIL): 1 = the r word not landed (qkd_kv_stack_relays_l MUT 2: o_emb one
edge early), 2 = h not landed (qkd_kv_es_fan_stack_bl MUT 2: o_pc one edge early), 3 = the fan word one bit low
(qkd_kv_stack_relays_l MUT 1).
    python3 tools/qwen_kv_die/hroot_land_bench.py [--mut N] [--edges 2000] --out DIR
Needs the kit design point env (tools/qwen_kv_die/kvs_kits_env.sh).  One line 'HROOT_LAND PASS|FAIL ...'; exit 0 only
on PASS.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MASTER = 'qkd_kvs_hroot'
MUT_SUB = {1: ('qkd_kv_stack_relays_l #(', 'qkd_kv_stack_relays_l #(.MUT(2), ', 'r word not landed'),
           2: ('qkd_kv_es_fan_stack_bl #(.MUT(0))', 'qkd_kv_es_fan_stack_bl #(.MUT(2))', 'h not landed'),
           3: ('qkd_kv_stack_relays_l #(', 'qkd_kv_stack_relays_l #(.MUT(1), ', 'fan word one bit low')}


def gen(land):
    env = dict(os.environ, OT_KV_STATIC_DIE='1', OT_KV_HROOT='1', OT_KV_FANFOLD='1', OT_KV_TILE_KITS='1',
               OT_KV_HROOT_LAND='1' if land else '0')
    code = ('import sys, json; sys.path.insert(0, %r); import kv_static_die as S; T = S.all_tiles(); '
            'd = next(v for v in T.values() if v["kind"] == "hroot"); txt = S.module_text(d, %r); '
            'print(json.dumps(dict(text=txt, src=S.sources(), rtl=S.RTL_FILE, '
            'ports=[(p, v["dir"], v["width"], v["cls"]) for p, v in d["ports"].items()])))') % (str(HERE), MASTER)
    return json.loads(subprocess.check_output([sys.executable, '-c', code], env=env, cwd=ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mut', type=int, default=0, choices=[0, *MUT_SUB])
    ap.add_argument('--edges', type=int, default=2000)
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    old, new = gen(False), gen(True)
    if new['rtl'] == old['rtl'] or 'qkd_kv_stack_relays_l' not in new['text']:
        raise SystemExit('hroot_land_bench: OT_KV_HROOT_LAND did not change the hroot tile')
    nt, what = new['text'], 'none'
    if a.mut:
        o_, n_, what = MUT_SUB[a.mut]
        if o_ not in nt:
            raise SystemExit(f'hroot_land_bench: mutant {a.mut} found no site')
        nt = nt.replace(o_, n_, 1)
    if old['ports'] != new['ports']:
        raise SystemExit('hroot_land_bench: ports differ between the landed and the unlanded tile')
    (out / 'tiles.sv').write_text('`timescale 1ns/1ps\n' + old['text'].replace(f'module {MASTER} (', 'module old_tile (', 1)
                                  + '\n' + nt.replace(f'module {MASTER} (', 'module new_tile (', 1) + '\n')
    po = old['ports']
    ins = [(p, w, c) for p, d, w, c in po if d == 'input' and c != 'clock']
    outs = [(p, w) for p, d, w, c in po if d == 'output']
    late = [(p, w) for p, w, c in ins if c not in ('reset', 'pad')]
    L = ['`timescale 1ns/1ps', 'module tb_hroot_land;', '  reg ck = 0; always #1 ck = ~ck;', '  integer t, bad, chk, act;']
    for p, w, c in ins:
        L.append(f'  reg [{w - 1}:0] {p};')
    for p, w in late:
        L.append(f'  reg [{w - 1}:0] dl__{p};')
    L.append('  always @(posedge ck) begin ' + ' '.join(f'dl__{p} <= {p};' for p, w in late) + ' end')
    for p, w in outs:
        L.append(f'  wire [{w - 1}:0] o__{p}, n__{p};')
    lat = {p for p, w in late}
    L.append('  old_tile u_old (' + ', '.join(
        f'.{p}({"ck" if c == "clock" else (("dl__" + p if p in lat else p) if d == "input" else "o__" + p)})'
        for p, d, w, c in po) + ');')
    L.append('  new_tile u_new (' + ', '.join(
        f'.{p}({"ck" if c == "clock" else (p if d == "input" else "n__" + p)})' for p, d, w, c in po) + ');')
    rnd = lambda w: '{' + ', '.join(['$random'] * ((w + 31) // 32)) + '}'     # noqa: E731
    L += ['  initial begin', '    bad = 0; chk = 0; act = 0;']
    L += [f'    {p} = 0;' for p, w, c in ins]
    L.append('    repeat (6) @(negedge ck);')
    L.append('    ' + ' '.join(f'{p} = 1;' for p, w, c in ins if c in ('reset', 'pad')))
    L.append(f'    for (t = 0; t < {2 * a.edges}; t = t + 1) begin')
    L.append('      @(negedge ck);')
    L += [f'      {p} = {rnd(w)};' for p, w in late]
    L.append('      #0.5;')
    L.append('      if (t > 3) begin')
    for p, w in outs:
        L.append(f'        chk = chk + 1; if (o__{p} !== n__{p}) begin bad = bad + 1; '
                 f'if (bad < 6) $display("MISMATCH t=%0d out {p}", t); end')
        L.append(f'        if (n__{p} != 0) act = act + 1;')
    L.append('      end')
    L.append('    end')
    L.append(f'    if (bad == 0) $display("HROOT_LAND PASS tile=hroot edges={2 * a.edges} checks=%0d active_out=%0d '
             f'outs={len(outs)} delayed_inputs={len(late)} errors=0 mut={a.mut} vs=unlanded_tile_inputs_plus1", chk, act);')
    L.append(f'    else $display("HROOT_LAND FAIL tile=hroot edges={2 * a.edges} checks=%0d errors=%0d mut={a.mut} '
             f'({what})", chk, bad);')
    L += ['    $finish;', '  end', 'endmodule']
    (out / 'tb.sv').write_text('\n'.join(L) + '\n')
    # the unlanded tile's u_rly (qkd_kv_stack_relays) is body text, not a join member: its file is not in S.sources()
    srcs = sorted((set(old['src']) | set(new['src']) | {'rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_half_root.sv'})
                  - {old['rtl'], new['rtl']})
    dirs = sorted({str(Path(s).parent) for s in srcs})
    cmd = ['verilator', '--binary', '--timing', '-j', str(a.threads), '-Wno-fatal', '-Wno-lint', '-Wno-style',
           '-Wno-TIMESCALEMOD', '--top-module', 'tb_hroot_land', '-Mdir', str(out / 'obj'), '-o', 'sim',
           str(out / 'tb.sv'), str(out / 'tiles.sv')] + srcs + ['+libext+.sv+.v'] + [x for d in dirs for x in ('-y', d)]
    print('SIM ' + subprocess.run(['verilator', '--version'], capture_output=True, text=True).stdout.strip())
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        print(f'HROOT_LAND FAIL tile=hroot build mut={a.mut} ')
        return 2
    r = subprocess.run([str(out / 'obj' / 'sim')], capture_output=True, text=True, cwd=ROOT)
    print(r.stdout[-4000:])
    line = [ln for ln in r.stdout.splitlines() if ln.startswith('HROOT_LAND ')]
    if not line:
        print(f'HROOT_LAND FAIL tile=hroot no verdict mut={a.mut} ')
        return 1
    return 0 if line[-1].startswith('HROOT_LAND PASS') else 1


if __name__ == '__main__':
    sys.exit(main())
