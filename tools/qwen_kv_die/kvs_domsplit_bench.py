#!/usr/bin/env python3
"""KV-DOMSPLIT 2026-10-19: lockstep bench of a DOMAIN-SPLIT KV kit tile (OT_KV_DOMSPLIT=1) against the unsplit tile of the
same design point (OT_KV_DOMSPLIT unset), both regenerated here from tools/qwen_kv_die/kv_static_die.py (no stale file).

The split moves bundle fields between ports (P -> P (ck fields) + P_h (hck fields)); the bench maps every field by its
producer key (the generator's bundle layout), so:
  * inputs: the unsplit tile's bundle inputs get random words; the split tile's P / P_h are wired from the SAME bits;
  * outputs: every split output bit equals the unsplit output bit of the same field, every edge after reset;
  * the group gather o_ctl: equal, except the landed hck status bits (kv_static_die domsplit_land), which must equal the
    unsplit bit of TWO ck edges earlier (qkd_kv_lvl_land, 2-flop landing);
  * every input pin of every shared child (u_old.u_<c>.<p> vs u_new.u_<c>.<p>) equal: the wiring into the children.
Phase A: natural behaviour; phase B: every shared child-output wire w_* FORCED to the same random value in both tiles.
--mut (split tile only, must FAIL): 1 = one child-output slice in a tile-output assign dropped; 2 = two equal-width input
connections of one child swapped; 4 = landing with one flop (grp / grp_h) | two equal-width hck input fields swapped (pc /
pc_h); 5 = landing bit 0 not landed (grp / grp_h) | an hck field moved onto the ck word (pc / pc_h: i_grp_h slice read from
i_grp).
    python3 tools/qwen_kv_die/kvs_domsplit_bench.py --tile grp|grp_h|pc|pc_h [--mut N] [--edges 1000] --out DIR
Needs the kit design-point env (source tools/qwen_kv_die/kvs_kits_env.sh; OT_KV_MU=1 for the MU point).
One line 'KVS_DOMSPLIT PASS|FAIL tile=<t> ...'; exit 0 only on PASS.
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
sys.path.insert(0, str(HERE))
import kvs_tile_bench as KTB  # noqa: E402

TILES = ('grp', 'grp_h', 'pc', 'pc_h')


def gen(t, split):
    env = dict(os.environ, OT_KV_STATIC_DIE='1', OT_KV_TILE_KITS='1', OT_KV_DOMSPLIT='1' if split else '0')
    code = ('import sys, json; sys.path.insert(0, %r); import kv_static_die as S; import kvs_tile_kits_rep as R; '
            'T = S.all_tiles(); d = next(v for v in T.values() if v["kind"] == %r); I = S.ins(); '
            'txt = S.module_text(d, S.KIND_MASTER[%r]); '
            'k = lambda key: S.ds_key(key) if isinstance(key, tuple) and len(key) == 4 else repr(key); '
            'print(json.dumps(dict(rtl=S.RTL_FILE, text=txt, src=sorted(set(S.sources()) | set(R.tile_sources(S, %r, "sim")[0])), '
            'ports=[(p, v["dir"], v["width"], v["cls"]) for p, v in d["ports"].items()], '
            'layout={p: [(pn, w, k(key)) for pn, w, key in v["layout"]] for p, v in d["ports"].items() '
            'if v.get("layout") and sum(e[1] for e in v["layout"]) == v["width"]}, '
            'land=d.get("domsplit_land"), '
            'children=[(S.cluster_of(n)[2], I[n]["module"], [(p, v["width"]) for p, v in S.spec(n).items() '
            'if v["direction"] != "output"]) for n in d["members"]])))') % (str(HERE), t, t, t)
    return json.loads(subprocess.check_output([sys.executable, '-c', code], env=env, cwd=ROOT))


def field_map(old, new):
    """{new port: [(new lo, old port, old lo, w)]} for every split bundle port, from the producer keys"""
    where = {}
    for p, lst in old['layout'].items():
        o_ = 0
        for _pn, w, key in lst:
            where[(p, key)] = (p, o_, w)
            o_ += w
    out = {}
    for q, lst in new['layout'].items():
        base = q[:-2] if q.endswith('_h') else q
        o_, rows = 0, []
        for _pn, w, key in lst:
            if (base, key) not in where:
                raise SystemExit(f'kvs_domsplit_bench: field {key} of {q} is not in the unsplit {base}')
            p, lo, w0 = where[(base, key)]
            if w0 != w:
                raise SystemExit(f'kvs_domsplit_bench: field {key} of {q} came from {p} ({w0} b), expected {base} ({w} b)')
            rows.append((o_, p, lo, w))
            o_ += w
        out[q] = rows
    return out


def mutate(t, txt, mut):
    if mut in (1, 2):
        return KTB.mutate(txt, mut)[::2]
    lines = txt.split('\n')
    if t in ('grp', 'grp_h'):
        for i, ln in enumerate(lines):
            m = re.match(r'(\s*qkd_kv_lvl_land #\(\.W\((\d+)\))\)', ln)
            if m:
                lines[i] = ln.replace(m.group(1), m.group(1) + f', .MUT({1 if mut == 4 else 2})', 1)
                return '\n'.join(lines), f'landing MUT={1 if mut == 4 else 2}'
    else:
        pk = [(i, m) for i, ln in enumerate(lines) for m in [re.match(r'(\s*wire \[(\d+):0\] \w+ = )(i_grp_h)\[(\d+):(\d+)\];$', ln)] if m]
        if mut == 4:
            for a in range(len(pk)):
                for b in range(a + 1, len(pk)):
                    (ia, ma), (ib, mb) = pk[a], pk[b]
                    if ma.group(2) == mb.group(2):
                        sa, sb = f'[{ma.group(4)}:{ma.group(5)}]', f'[{mb.group(4)}:{mb.group(5)}]'
                        lines[ia], lines[ib] = lines[ia].replace(sa, sb), lines[ib].replace(sb, sa)
                        return '\n'.join(lines), f'swapped i_grp_h{sa} <-> {sb}'
        if mut == 5 and pk:
            i, m = pk[-1]
            w_ = int(m.group(4)) - int(m.group(5)) + 1
            lines[i] = lines[i].replace(f'= i_grp_h[{m.group(4)}:{m.group(5)}]', f'= i_grp[{w_ - 1}:0]', 1)
            return '\n'.join(lines), f'hck field read from the ck word ({m.group(4)}:{m.group(5)})'
    raise SystemExit(f'kvs_domsplit_bench: mutant {mut} found no site in {t}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tile', required=True, choices=TILES)
    ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--edges', type=int, default=1000)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sim', default=os.environ.get('KVS_SIM', 'verilator'), choices=('iverilog', 'verilator'))
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--prepare', action='store_true',
                    help='write tb.sv / tiles.sv / cmd.json only (the sim runs later on the fleet: --run-prepared DIR)')
    a = ap.parse_args()
    t = a.tile
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    old, new = gen(t, False), gen(t, True)
    ntext, what = (new['text'], 'none') if a.mut == 0 else mutate(t, new['text'], a.mut)
    nm = KTB.MASTER[t]
    (out / 'tiles.sv').write_text('`timescale 1ns/1ps\n' + old['text'].replace(f'module {nm} (', 'module old_tile (', 1) +
                                  '\n' + ntext.replace(f'module {nm} (', 'module new_tile (', 1) + '\n')
    fm = field_map(old, new)
    po, pn = old['ports'], new['ports']
    pod = {p: (d, w, c) for p, d, w, c in po}
    L = ['`timescale 1ns/1ps', 'module tb_kvs_domsplit;', '  reg ck = 0; always #1 ck = ~ck;',
         '  integer t, bad, chk, act, nland; reg phb;']
    ins = [(p, w, c) for p, d, w, c in po if d == 'input' and c != 'clock']
    for p, w, c in ins:
        L.append(f'  reg [{w - 1}:0] {p};')
    outs = [(p, w) for p, d, w, c in po if d == 'output']
    for p, w in outs:
        L.append(f'  wire [{w - 1}:0] o__{p};')
    for p, d, w, c in pn:
        if d == 'output':
            L.append(f'  wire [{w - 1}:0] n__{p};')

    def cat(rows, pre):
        return '{' + ', '.join(f'{pre}{p}[{lo + w - 1}:{lo}]' for _o, p, lo, w in reversed(rows)) + '}'

    conn = []
    for p, d, w, c in pn:
        if c == 'clock':
            conn.append(f'.{p}(ck)')
        elif d == 'input':
            if p in fm:
                conn.append(f'.{p}({cat(fm[p], "")})')
            elif p in pod and pod[p][:2] == ('input', w):
                conn.append(f'.{p}({p})')
            else:
                raise SystemExit(f'kvs_domsplit_bench: split input {p} has no unsplit source')
        else:
            conn.append(f'.{p}(n__{p})')
    L.append('  old_tile u_old (' + ', '.join(
        f'.{p}({"ck" if c == "clock" else (p if d == "input" else "o__" + p)})' for p, d, w, c in po) + ');')
    L.append('  new_tile u_new (' + ', '.join(conn) + ');')
    # expected split outputs (old bits) + the landed gather bits
    land = new.get('land') or {}
    gw = land.get('word_width')
    lbits = set()
    if land:
        copies = range(pod['o_ctl'][1] // gw) if t == 'grp_h' else range(1)
        lbits = {b + s * gw for s in copies for b in land['bits']}
    checks = []
    for p, d, w, c in pn:
        if d != 'output':
            continue
        if p in fm:
            checks.append((p, cat(fm[p], 'o__')))
        elif p in pod and pod[p][:2] == ('output', w):
            checks.append((p, None))
        else:
            raise SystemExit(f'kvs_domsplit_bench: split output {p} has no unsplit counterpart')
    covered = {(p, lo + i) for rows in fm.values() for _o, p, lo, w in rows for i in range(w)}
    direct = {q for q, e in checks if e is None}
    for p, d, w, c in po:     # every unsplit port bit is checked / driven exactly once
        if c == 'clock' or p in direct or (d == 'input' and p not in fm and p in {q for q, *_ in pn}):
            continue
        if sum((p, b) in covered for b in range(w)) != w or sum(len(r) for r in fm.values()) == 0:
            raise SystemExit(f'kvs_domsplit_bench: unsplit port {p} not fully covered by the split ports')
    if lbits:
        L.append(f'  reg [{pod["o_ctl"][1] - 1}:0] h1, h2;')
    rnd = lambda w: '{' + ', '.join(['$random'] * ((w + 31) // 32)) + '}'     # noqa: E731
    ow = dict((n, int(w)) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', old['text']))
    nw = dict((n, int(w)) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', ntext))
    frc = sorted(n for n in ow if n in nw and ow[n] == nw[n])
    for n in frc:
        L.append(f'  reg [{ow[n]}:0] f_{n};')
    cin = [(loc, p, w) for loc, mod, ps in old['children'] for p, w in ps]
    L.append('  initial begin')
    L.append('    bad = 0; chk = 0; act = 0; nland = 0; phb = 0;')
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
        if n.startswith(('w_wrn__es', 'w_wrn__expected_valid')):
            L.append(f'      f_{n} = ($random % 4 == 0) ? {rnd(ow[n] + 1)} : 0;')
        else:
            L.append(f'      f_{n} = {rnd(ow[n] + 1)};')
    L.append('      #0.5;')
    L.append('      if (t > 2) begin')
    for p, exp in checks:
        if p == 'o_ctl' and lbits:
            for b in range(pod['o_ctl'][1]):
                ref = f'h2[{b}]' if b in lbits else f'o__o_ctl[{b}]'
                L.append(f'        chk = chk + 1; if (n__o_ctl[{b}] !== {ref}) begin bad = bad + 1; '
                         f'if (bad < 6) $display("MISMATCH t=%0d out o_ctl[{b}]{" landed" if b in lbits else ""}", t); end')
            L.append('        if (n__o_ctl != 0) act = act + 1;')
            continue
        e = exp or f'o__{p}'
        L.append(f'        chk = chk + 1; if (n__{p} !== {e}) begin bad = bad + 1; '
                 f'if (bad < 6) $display("MISMATCH t=%0d out {p}", t); end')
        L.append(f'        if (n__{p} != 0) act = act + 1;')
    for loc, p, w in cin:
        L.append(f'        chk = chk + 1; if (u_old.u_{loc}.{p} !== u_new.u_{loc}.{p}) begin bad = bad + 1; '
                 f'if (bad < 6) $display("MISMATCH t=%0d child u_{loc}.{p}", t); end')
    if lbits:
        L.append('        if ((h2 ^ o__o_ctl) & ' + f"{pod['o_ctl'][1]}'b" +
                 ''.join('1' if b in lbits else '0' for b in reversed(range(pod['o_ctl'][1]))) + ') nland = nland + 1;')
    L.append('      end')
    if lbits:
        L.append('      h2 = h1; h1 = o__o_ctl;')
    L.append('    end')
    L.append(f'    if (bad == 0) $display("KVS_DOMSPLIT PASS tile={t} edges={2 * a.edges} checks=%0d active_out=%0d '
             f'split_ports={len(fm)} child_inputs={len(cin)} forced={len(frc)} landed_bits={len(lbits)} '
             f'landed_changes=%0d errors=0 mut={a.mut} vs=unsplit_tile", chk, act, nland);')
    L.append(f'    else $display("KVS_DOMSPLIT FAIL tile={t} edges={2 * a.edges} checks=%0d errors=%0d mut={a.mut} '
             f'({what})", chk, bad);')
    L.append('    $finish;')
    L.append('  end')
    L.append('endmodule')
    (out / 'tb.sv').write_text('\n'.join(L) + '\n')
    srcs = sorted((set(old['src']) | set(new['src'])) - {old['rtl'], new['rtl']})
    (out / 'sources.txt').write_text('\n'.join(srcs) + '\n')
    dirs = sorted({str(Path(s).parent) for s in srcs})
    if a.sim == 'verilator':
        cmd = ['verilator', '--binary', '--timing', '-j', str(a.threads), '-Wno-fatal', '-Wno-lint', '-Wno-style',
               '-Wno-TIMESCALEMOD', '--top-module', 'tb_kvs_domsplit', '-Mdir', str(out / 'obj'), '-o', 'sim',
               str(out / 'tb.sv'), str(out / 'tiles.sv')] + list(srcs) + ['+libext+.sv+.v'] + [x for d in dirs for x in ('-y', d)]
        run = [str(out / 'obj' / 'sim')]
    else:
        cmd = ['iverilog', '-g2012', '-o', str(out / 'sim'), '-s', 'tb_kvs_domsplit', str(out / 'tb.sv'),
               str(out / 'tiles.sv')] + list(srcs) + ['-Y', '.sv'] + [x for d in dirs for x in ('-y', d)]
        run = ['vvp', '-n', str(out / 'sim')]
    o_ = str(out)
    rel_ = lambda xs: [x.replace(o_, '{OUT}') for x in xs]      # noqa: E731
    (out / 'cmd.json').write_text(json.dumps(dict(tile=t, mut=a.mut, sim=a.sim, build=rel_(cmd), run=rel_(run)), indent=1) + '\n')
    if a.prepare:
        print(f'prepared {out} (tile {t} mut {a.mut}: {what})')
        return 0
    return run_prepared(out)


def run_prepared(out):
    """build + run a prepared bench dir from the repository (or extracted source) root"""
    out = Path(out).resolve()
    c = json.loads((out / 'cmd.json').read_text())
    sub = lambda xs: [x.replace('{OUT}', str(out)) for x in xs]   # noqa: E731
    t, mut = c['tile'], c['mut']
    if c['sim'] == 'verilator':
        print('SIM ' + subprocess.run(['verilator', '--version'], capture_output=True, text=True).stdout.strip())
    r = subprocess.run(sub(c['build']), capture_output=True, text=True, cwd=os.getcwd())
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        print(f'KVS_DOMSPLIT FAIL tile={t} build mut={mut} ')
        return 2
    r = subprocess.run(sub(c['run']), capture_output=True, text=True, cwd=os.getcwd())
    print(r.stdout[-4000:])
    line = [ln for ln in r.stdout.splitlines() if ln.startswith('KVS_DOMSPLIT ')]
    if not line:
        print(f'KVS_DOMSPLIT FAIL tile={t} no verdict mut={mut} ')
        return 1
    return 0 if line[-1].startswith('KVS_DOMSPLIT PASS') else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--run-prepared':
        sys.exit(run_prepared(sys.argv[2]))
    sys.exit(main())
