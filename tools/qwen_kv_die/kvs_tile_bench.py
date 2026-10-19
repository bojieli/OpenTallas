#!/usr/bin/env python3
"""KV-INTEG/KITS-A 2026-10-18: lockstep bench of a singleton static tile KIT TOP (qkd_kvs_ctl / _attn / _emb generated
with OT_KV_TILE_KITS=1: one clock port ck, hard children without #()) against the DIE-BOUND tile of the same design point
(OT_KV_TILE_KITS unset: one '<child>__ck' port per child, every one on the same die trunk clk_core_c).  Both tiles are
regenerated here from tools/qwen_kv_die/kv_static_die.py (the bench never reads a stale tile file).

Every edge from reset, both tiles get the same random inputs (resets low for 6 edges); checked every edge after reset:
  * every tile output equal (!==, X / Z count as values);
  * every input port of every child instance equal (u_old.u_<c>.<p> vs u_new.u_<c>.<p>): the wiring INTO the children
    is compared directly, independent of what the children do with it.
Phase A (edges [0, E)): natural behaviour.  Phase B (edges [E, 2E)): every child output wire w_* is FORCED to the same
random value in both tiles each edge (sparse for the writer's es / expected_valid events), so every child -> child and
child -> tile-output wire carries random data.
--mut (applied to the KIT TOP only; must FAIL): 1 = one child-output slice in a tile-output assign replaced by zeros
(dropped wire); 2 = two equal-width input connections of one child swapped; 3 = the first child whose outputs reach a
tile output removed (missing child).
    python3 tools/qwen_kv_die/kvs_tile_bench.py --tile ctl|attn|emb [--mut N] [--edges 2000] --out DIR
Needs (as kv_static_die): OT_KV_STATIC_DIE=1 + the design-point env (kvj-g2-env.sh, OT_KV_HROOT=1 OT_KV_FANFOLD=1).
One line 'KVS_TILE PASS|FAIL tile=<t> ...'; exit 0 only on PASS.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# KV-INTEG2: singletons by instance, replicated kinds (KITS-B) by the first die instance of the kind (every instance of a
# kind is the same master)
INST = dict(ctl='kvs_ctl', attn='kvs_attn', emb='kvs_emb', grp=None, grp_h=None, pc=None, pc_h=None, hroot=None)
MASTER = {k: f'qkd_kvs_{k}' for k in INST}


def gen(t, ck1):
    env = dict(os.environ, OT_KV_STATIC_DIE='1', OT_KV_TILE_KITS='1' if ck1 else '0')
    code = ('import sys, json; sys.path.insert(0, %r); import kv_static_die as S; T = S.all_tiles(); k_ = %r; d = T[k_] if k_ else next(v for v in T.values() if v["kind"] == %r); '
            'I = S.ins(); txt = S.module_text(d, %r); '
            'print(json.dumps(dict(rtl=S.RTL_FILE, text=txt, src=S.sources(), '
            'ports=[(p, v["dir"], v["width"], v["cls"]) for p, v in d["ports"].items()], '
            'children=[(S.cluster_of(n)[2], I[n]["module"], [(p, v["width"]) for p, v in S.spec(n).items() '
            'if v["direction"] != "output"]) for n in d["members"]])))') % (str(HERE), INST[t], t, MASTER[t])
    return json.loads(subprocess.check_output([sys.executable, '-c', code], env=env, cwd=ROOT))


def mutate(txt, mut):
    """returns (mutated text, removed child loc or None, description)"""
    lines = txt.split('\n')
    if mut == 1:
        for i, ln in enumerate(lines):
            m = re.match(r'\s*assign (\w+) = (.*);$', ln)
            if not m:
                continue
            s = re.search(r'(w_\w+)\[(\d+):(\d+)\]', m.group(2))
            if s:
                w = int(s.group(2)) - int(s.group(3)) + 1
                lines[i] = ln.replace(s.group(0), f"{{{w}{{1'b0}}}}", 1)
                return '\n'.join(lines), None, f'dropped {s.group(0)} in assign {m.group(1)}'
        wd = dict((n, int(w) + 1) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', txt))
        for i, ln in enumerate(lines):         # KV-INTEG2: a whole child-output wire on a tile output (no slice)
            m = re.match(r'\s*assign (\w+) = (w_\w+);$', ln)
            if m and m.group(2) in wd:
                lines[i] = ln.replace(f'= {m.group(2)};', f"= {{{wd[m.group(2)]}{{1'b0}}}};", 1)
                return '\n'.join(lines), None, f'dropped {m.group(2)} in assign {m.group(1)}'
    if mut == 2:
        for i, ln in enumerate(lines):
            m = re.match(r'(\s*\w+(?: #\(.*?\))? u_\w+ \()(.*)(\);)$', ln)
            if not m:
                continue
            conns = re.findall(r'\.(\w+)\(([^()]*)\)', m.group(2))
            def width(e):
                s = re.fullmatch(r'\w+\[(\d+):(\d+)\]', e.strip())
                return int(s.group(1)) - int(s.group(2)) + 1 if s else None
            for a in range(len(conns)):
                for b in range(a + 1, len(conns)):
                    wa, wb = width(conns[a][1]), width(conns[b][1])
                    if wa and wa == wb and wa > 1 and conns[a][1] != conns[b][1]:
                        (pa, ea), (pb, eb) = conns[a], conns[b]
                        new = ln.replace(f'.{pa}({ea})', '\x00A', 1).replace(f'.{pb}({eb})', f'.{pb}({ea})', 1)
                        new = new.replace('\x00A', f'.{pa}({eb})', 1)
                        lines[i] = new
                        return '\n'.join(lines), None, f'swapped .{pa}({ea}) <-> .{pb}({eb})'
    if mut == 3:
        assigns = '\n'.join(ln for ln in lines if ln.strip().startswith('assign '))
        for i, ln in enumerate(lines):
            m = re.match(r'\s*\w+(?: #\(.*?\))? u_(\w+) \(', ln)
            if m and f'w_{m.group(1)}__' in assigns:
                del lines[i]
                return '\n'.join(lines), m.group(1), f'removed child u_{m.group(1)}'
    raise SystemExit(f'kvs_tile_bench: mutant {mut} found no site')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tile', required=True, choices=sorted(INST))
    ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--edges', type=int, default=2000)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sim', default=os.environ.get('KVS_SIM', 'iverilog'), choices=('iverilog', 'verilator'))
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    t = a.tile
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    old, new = gen(t, False), gen(t, True)
    ntext, gone, what = (new['text'], None, 'none') if a.mut == 0 else mutate(new['text'], a.mut)
    nm = MASTER[t]
    (out / 'tiles.sv').write_text('`timescale 1ns/1ps\n' + old['text'].replace(f'module {nm} (', 'module old_tile (', 1) +
                                  '\n' + ntext.replace(f'module {nm} (', 'module new_tile (', 1) + '\n')
    po, pn = old['ports'], new['ports']
    pnd = {p: (d, w, c) for p, d, w, c in pn}
    L = ['`timescale 1ns/1ps', 'module tb_kvs_tile;', '  reg ck = 0; always #1 ck = ~ck;',
         '  integer t, bad, chk, act; reg phb;']
    ins = [(p, w, c) for p, d, w, c in po if d == 'input' and c != 'clock']
    for p, w, c in ins:
        if p not in pnd or pnd[p][0] != 'input' or pnd[p][1] != w:
            raise SystemExit(f'kvs_tile_bench: input {p} differs between the die-bound tile and the kit top')
        L.append(f'  reg [{w - 1}:0] {p};')
    outs = [(p, w) for p, d, w, c in po if d == 'output']
    if sorted(outs) != sorted((p, w) for p, d, w, c in pn if d == 'output'):
        raise SystemExit('kvs_tile_bench: outputs differ between the die-bound tile and the kit top')
    if not set(p for p, d, w, c in pn if c == 'clock') <= {'ck', 'hck'} or 'ck' not in [p for p, d, w, c in pn]:
        raise SystemExit('kvs_tile_bench: the kit top must have one clock port per domain (ck [, hck])')
    for p, w in outs:
        L.append(f'  wire [{w - 1}:0] o__{p}, n__{p};')
    L.append('  old_tile u_old (' + ', '.join(
        f'.{p}({"ck" if c == "clock" else (p if d == "input" else "o__" + p)})' for p, d, w, c in po) + ');')
    L.append('  new_tile u_new (' + ', '.join(
        f'.{p}({"ck" if c == "clock" else (p if d == "input" else "n__" + p)})' for p, d, w, c in pn) + ');')
    rnd = lambda w: '{' + ', '.join(['$random'] * ((w + 31) // 32)) + '}'     # noqa: E731
    ow = dict((n, int(w)) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', old['text']))
    nw = dict((n, int(w)) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', ntext))
    frc = sorted(n for n in ow if n in nw and ow[n] == nw[n] and not (gone and n.startswith(f'w_{gone}__')))
    for n in frc:
        L.append(f'  reg [{ow[n]}:0] f_{n};')
    cin = [(loc, p, w) for loc, mod, ps in new['children'] for p, w in ps if loc != gone]
    L.append('  initial begin')
    L.append('    bad = 0; chk = 0; act = 0; phb = 0;')
    for p, w, c in ins:
        L.append(f'    {p} = 0;')
    L.append('    repeat (6) @(negedge ck);')
    L.append('    ' + ' '.join(f"{p} = 1;" for p, w, c in ins if c in ('reset', 'pad')))
    L.append(f'    for (t = 0; t < {2 * a.edges}; t = t + 1) begin')
    L.append('      @(negedge ck);')
    L.append(f'      if (t == {a.edges}) begin phb = 1;')
    for n in frc:
        L.append(f'        force u_old.{n} = f_{n}; force u_new.{n} = f_{n};')
    L.append('      end')
    for p, w, c in ins:
        if c in ('reset', 'pad'):
            continue
        L.append(f'      {p} = {rnd(w)};')
    for n in frc:
        if n.startswith(('w_wrn__es', 'w_wrn__expected_valid')):      # sparse writer events (two-lane rule)
            L.append(f'      f_{n} = ($random % 4 == 0) ? {rnd(ow[n] + 1)} : 0;')
        else:
            L.append(f'      f_{n} = {rnd(ow[n] + 1)};')
    L.append('      #0.5;')
    L.append('      if (t > 2) begin')
    for p, w in outs:
        L.append(f'        chk = chk + 1; if (o__{p} !== n__{p}) begin bad = bad + 1; '
                 f'if (bad < 6) $display("MISMATCH t=%0d out {p}", t); end')
        L.append(f'        if (n__{p} != 0) act = act + 1;')
    for loc, p, w in cin:
        L.append(f'        chk = chk + 1; if (u_old.u_{loc}.{p} !== u_new.u_{loc}.{p}) begin bad = bad + 1; '
                 f'if (bad < 6) $display("MISMATCH t=%0d child u_{loc}.{p}", t); end')
    L.append('      end')
    L.append('    end')
    L.append(f'    if (bad == 0) $display("KVS_TILE PASS tile={t} edges={2 * a.edges} checks=%0d active_out=%0d '
             f'outs={len(outs)} child_inputs={len(cin)} forced={len(frc)} errors=0 mut={a.mut} vs=die_bound_tile", chk, act);')
    L.append(f'    else $display("KVS_TILE FAIL tile={t} edges={2 * a.edges} checks=%0d errors=%0d mut={a.mut} '
             f'({what})", chk, bad);')
    L.append('    $finish;')
    L.append('  end')
    L.append('endmodule')
    (out / 'tb.sv').write_text('\n'.join(L) + '\n')
    # KV-INTEG2: the explicit module closure of the tile (kvs_tile_kits_rep.tile_sources: SRAM models, modules defined in a
    # file of another name), plus kv_static_die.sources(); the generated tile file itself is replaced by tiles.sv
    code = ('import sys, json; sys.path.insert(0, %r); import kv_static_die as S; import kvs_tile_kits_rep as R; '
            'print(json.dumps(R.tile_sources(S, %r, "sim")[0]))') % (str(HERE), t)
    cl = json.loads(subprocess.check_output([sys.executable, '-c', code], cwd=ROOT,
                                            env=dict(os.environ, OT_KV_STATIC_DIE='1', OT_KV_TILE_KITS='1')))
    srcs = sorted((set(old['src']) | set(new['src']) | set(cl)) - {old['rtl'], new['rtl']})
    dirs = sorted({str(Path(s).parent) for s in srcs})
    if a.sim == 'verilator':
        # KV-KITS-ATTN 10-18: the closure daemon's pinned Verilator (5.050, PATH set by the loop / kvs_tile_bench.sh)
        cmd = ['verilator', '--binary', '--timing', '-j', str(a.threads), '-Wno-fatal', '-Wno-lint', '-Wno-style',
               '-Wno-TIMESCALEMOD', '--top-module', 'tb_kvs_tile', '-Mdir', str(out / 'obj'), '-o', 'sim',
               str(out / 'tb.sv'), str(out / 'tiles.sv')] + list(srcs) + ['+libext+.sv+.v'] + [x for d in dirs for x in ('-y', d)]
        run = [str(out / 'obj' / 'sim')]
        print('SIM ' + subprocess.run(['verilator', '--version'], capture_output=True, text=True).stdout.strip())
    else:
        cmd = ['iverilog', '-g2012', '-o', str(out / 'sim'), '-s', 'tb_kvs_tile', str(out / 'tb.sv'),
               str(out / 'tiles.sv')] + list(srcs) + ['-Y', '.sv'] + [x for d in dirs for x in ('-y', d)]
        run = ['vvp', '-n', str(out / 'sim')]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        print(f'KVS_TILE FAIL tile={t} build mut={a.mut} ')
        return 2
    r = subprocess.run(run, capture_output=True, text=True, cwd=ROOT)
    print(r.stdout[-4000:])
    line = [ln for ln in r.stdout.splitlines() if ln.startswith('KVS_TILE ')]
    if not line:
        print(f'KVS_TILE FAIL tile={t} no verdict mut={a.mut} ')
        return 1
    return 0 if line[-1].startswith('KVS_TILE PASS') else 1


if __name__ == '__main__':
    sys.exit(main())
