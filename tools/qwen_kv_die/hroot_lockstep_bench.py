#!/usr/bin/env python3
"""KV-PLAN 10-17 (HANDOFF 0cx+4 decision 1): lockstep bench of the DISTRIBUTED static control (control tile + four stack
root tiles, OT_KV_HROOT=1) against the single-root control tile (OT_KV_HROOT=0), on the generated tile RTL.

Both control tiles get the same random inputs every edge (the new tile's up words i_hroot_<H> = {i_fan_E, i_fan_W} of
the old tile).  Checked every edge: every common control-tile output equal; every stack fan's outputs (old fan fed by
old o_fan_<st>, new fan fed by the stack root's o_fan) one edge later; old o_kvpc_<st>_31 (es chain head) == the root's
o_pc one edge later; the root's up words == the fan gathers / return train one edge later.  Every child output wire of
the control tile except the es fan root's is forced to the same random value in both.  --mut 1 builds the roots with
qkd_kv_es_fan_stack / qkd_kv_stack_relays MUT 1 (must FAIL).
    python3 tools/qwen_kv_die/hroot_lockstep_bench.py [--mut 1] [--edges 3000] [--out DIR]
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def tiles(hroot):
    env = dict(os.environ, OT_KV_STATIC_DIE='1', OT_KV_HROOT='1' if hroot else '0')
    code = ('import sys, json; sys.path.insert(0, %r); import kv_static_die as S; t = S.all_tiles(); '
            'print(json.dumps(dict(rtl=S.RTL_FILE, src=S.sources(), ports={d: [(p, v["dir"], v["width"], v["cls"]) '
            'for p, v in t[d]["ports"].items()] for d in t if d in ("kvs_ctl", "kvs_hroot_WS", "kvs_fan_WS")})))' % str(HERE))
    import json
    return json.loads(subprocess.check_output([sys.executable, '-c', code], env=env, cwd=ROOT))


def module(path, name, rename):
    txt = (ROOT / path).read_text()
    m = re.search(r'(module ' + name + r' \(.*?endmodule)', txt, re.S)
    return m.group(1).replace(f'module {name} (', f'module {rename} (', 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--edges', type=int, default=3000)
    ap.add_argument('--out', default='/tmp/hroot_lockstep')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    old, new = tiles(False), tiles(True)
    (out / 'tiles.sv').write_text('`timescale 1ns/1ps\n' + module(old['rtl'], 'qkd_kvs_ctl', 'old_kvs_ctl') + '\n' +
                                  module(new['rtl'], 'qkd_kvs_ctl', 'new_kvs_ctl') + '\n' +
                                  module(new['rtl'], 'qkd_kvs_hroot', 'new_kvs_hroot') + '\n' +
                                  module(old['rtl'], 'qkd_kvs_fan', 'old_kvs_fan') + '\n' +
                                  module(new['rtl'], 'qkd_kvs_fan', 'new_kvs_fan') + '\n')
    po, pn, ph = old['ports']['kvs_ctl'], new['ports']['kvs_ctl'], new['ports']['kvs_hroot_WS']
    L = ['`timescale 1ns/1ps', 'module tb_hroot_lockstep;', '  reg ck = 0; always #1 ck = ~ck;', '  integer t, bad, tog, chv;']
    ins = [(p, w, c) for p, d, w, c in po if d == 'input']
    for p, w, c in ins:
        L.append(f'  reg [{w - 1}:0] {p};')
    for p, d, w, c in po:
        if d == 'output':
            L.append(f'  wire [{w - 1}:0] o__{p};')
    for p, d, w, c in pn:
        if d == 'output':
            L.append(f'  wire [{w - 1}:0] n__{p};')
    L.append('  old_kvs_ctl u_old (' + ', '.join(f'.{p}({p if d == "input" else "o__" + p})' for p, d, w, c in po) + ');')
    conn = []
    for p, d, w, c in pn:
        if d == 'output':
            conn.append(f'.{p}(n__{p})')
        elif p.startswith('i_hroot_'):
            conn.append(f'.{p}(i_fan_{p[8:]})')
        else:
            conn.append(f'.{p}({p})')
    L.append('  new_kvs_ctl u_new (' + ', '.join(conn) + ');')
    gw = dict((p, w) for p, d, w, c in ph)['i_g']
    rw = dict((p, w) for p, d, w, c in ph)['i_r']
    for k, st in enumerate(('WS', 'WN', 'ES', 'EN')):
        L.append(f'  reg [{rw - 1}:0] r{st};')
        for p, d, w, c in ph:
            if d == 'output':
                L.append(f'  wire [{w - 1}:0] h{st}__{p};')
        cc = []
        for p, d, w, c in ph:
            if d == 'output':
                cc.append(f'.{p}(h{st}__{p})')
            elif c == 'clock':
                cc.append(f'.{p}(ck)')
            elif p == 'rst_n':
                cc.append(f'.{p}(rst_n)')
            elif p == 'esh__stack':
                cc.append(f".{p}(2'd{k})")
            elif p == 'i_ctl':
                cc.append(f'.{p}(n__o_hroot_{st})')
            elif p == 'i_g':
                cc.append(f'.{p}(nf{st}__o_ctl)')
            elif p == 'i_r':
                cc.append(f'.{p}(r{st})')
        L.append(f'  new_kvs_hroot u_h{st} (' + ', '.join(cc) + ');')
    # the stack fans: old fan <- old o_fan_<st>, new fan <- the stack root's o_fan; same random group gathers
    pf_o, pf_n = old['ports']['kvs_fan_WS'], new['ports']['kvs_fan_WS']
    cmp_d = []
    for st, hn, s in (('WS', 'S', 'w'), ('ES', 'S', 'e'), ('WN', 'N', 'w'), ('EN', 'N', 'e')):
        for who, pf, src in (('of', pf_o, f'o__o_fan_{st}'), ('nf', pf_n, f'h{st}__o_fan')):
            cc = []
            for p, d, w, c in pf:
                if d == 'output':
                    L.append(f'  wire [{w - 1}:0] {who}{st}__{p};')
                    cc.append(f'.{p}({who}{st}__{p})')
                elif p == 'i_ctl':
                    cc.append(f'.{p}({src})')
                else:
                    cc.append(f'.{p}(fg{st}__{p})')
            L.append(f'  {"old" if who == "of" else "new"}_kvs_fan u_{who}{st} (' + ', '.join(cc) + ');')
        for p, d, w, c in pf_o:
            if d == 'input' and p != 'i_ctl':
                L.append(f'  reg [{w - 1}:0] fg{st}__{p};')
            if d == 'output' and p != 'o_ctl':
                L.append(f'  reg [{w - 1}:0] q{st}__{p}; always @(posedge ck) q{st}__{p} <= of{st}__{p};')
                cmp_d.append((f'q{st}__{p}', f'nf{st}__{p}'))
        L.append(f'  reg [{gw - 1}:0] qg{st}; always @(posedge ck) qg{st} <= nf{st}__o_ctl;')
        L.append(f'  reg [{rw - 1}:0] qr{st}; always @(posedge ck) qr{st} <= r{st};')
        w = dict((p, w) for p, d, w, c in po)[f'o_kvpc_{st}_31']
        L.append(f'  reg [{w - 1}:0] q__o_kvpc_{st}_31; always @(posedge ck) q__o_kvpc_{st}_31 <= o__o_kvpc_{st}_31;')
        cmp_d += [(f'qg{st}', f'h{st}__o_ctl'), (f'qr{st}', f'h{st}__o_emb'), (f'q__o_kvpc_{st}_31', f'h{st}__o_pc')]
    common = [p for p, d, w, c in po if d == 'output' and any(q == p and dd == 'output' for q, dd, _, _ in pn)]
    rnd = lambda w: '{' + ', '.join(['$random'] * ((w + 31) // 32)) + '}'     # noqa: E731
    # every child output wire of the control tile (except the es fan root's) is FORCED to the same random value in
    # both tiles each edge: the bench exercises every wire of the two compositions, not only what random die inputs
    # can provoke through the boot protocol; the es fan root runs on its (forced, random) writer / boot inputs
    ow = dict((n, int(w)) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', module(old['rtl'], 'qkd_kvs_ctl', 'x')))
    nw = dict((n, int(w)) for w, n in re.findall(r'wire \[(\d+):0\] (w_\w+);', module(new['rtl'], 'qkd_kvs_ctl', 'x')))
    frc = sorted(n for n in ow if n in nw and ow[n] == nw[n] and not n.startswith('w_fanr__'))
    for n in frc:
        L.append(f'  reg [{ow[n]}:0] f_{n};')
    L.append('  initial begin')
    for n in frc:
        L.append(f'    force u_old.{n} = f_{n}; force u_new.{n} = f_{n};')
    L.append('    bad = 0; tog = 0; chv = 0;')
    for p, w, c in ins:
        L.append(f'    {p} = 0;')
    L.append('    repeat (6) @(negedge ck);')
    L.append("    rst_n = 1; " + ' '.join(f"{p} = 1;" for p, w, c in ins if c == 'reset' and p != 'rst_n'))
    L.append(f'    for (t = 0; t < {a.edges}; t = t + 1) begin')
    L.append('      @(negedge ck);')
    for p, w, c in ins:
        if c in ('clock', 'reset', 'pad'):
            continue
        L.append(f'      {p} = {rnd(w)};')
    for st in ('WS', 'WN', 'ES', 'EN'):
        L.append(f'      r{st} = {rnd(rw)};')
    for n in frc:
        if n.startswith(('w_wrn__es', 'w_wrn__expected_valid')):      # sparse writer events (two-lane rule)
            L.append(f'      f_{n} = ($random % 4 == 0) ? {rnd(ow[n] + 1)} : 0;')
        else:
            L.append(f'      f_{n} = {rnd(ow[n] + 1)};')
    for st in ('WS', 'ES', 'WN', 'EN'):
        for p, d, w, c in pf_o:
            if d == 'input' and p != 'i_ctl':
                L.append(f'      fg{st}__{p} = {rnd(w)};')
    L.append('      if (t > 3) begin')
    for p in common:
        L.append(f'        if (o__{p} !== n__{p}) begin bad = bad + 1; if (bad < 5) $display("MISMATCH t=%0d common {p}", t); end')
    for qo, hn_ in cmp_d:
        L.append(f'        if ({qo} !== {hn_}) begin bad = bad + 1; if (bad < 5) $display("MISMATCH t=%0d {qo} vs {hn_}", t); end')
    L.append('        if (qES__o_ch0 != 0) tog = tog + 1;')
    L.append('        if (q__o_kvpc_WS_31 != 0 || q__o_kvpc_ES_31 != 0 || q__o_kvpc_WN_31 != 0 || q__o_kvpc_EN_31 != 0) chv = chv + 1;')
    L.append('      end')
    L.append('    end')
    L.append(f'    if (bad == 0) $display("PASS hroot lockstep %0d edges (%0d edges with a live fan word, %0d with a non-zero chain head) MUT={a.mut}", {a.edges}, tog, chv);')
    L.append(f'    else $display("FAIL %0d mismatches MUT={a.mut}", bad);')
    L.append('    $finish;')
    L.append('  end')
    L.append('endmodule')
    (out / 'tb.sv').write_text('\n'.join(L) + '\n')
    for p, d, w, c in po:
        if d == 'input' and c == 'clock':
            (out / 'tb.sv').write_text((out / 'tb.sv').read_text().replace(f'  reg [{w - 1}:0] {p};', f'  wire [{w - 1}:0] {p} = ck;', 1)
                                       .replace(f'    {p} = 0;\n', '', 1))
    srcs = sorted(set(old['src']) | set(new['src']))
    defs = []
    if a.mut:
        t_ = (out / 'tiles.sv').read_text().replace('qkd_kv_es_fan_stack #(.MUT(0))', f'qkd_kv_es_fan_stack #(.MUT({a.mut}))')
        t_ = t_.replace('qkd_kv_stack_relays #(', f'qkd_kv_stack_relays #(.MUT({a.mut}), ')
        (out / 'tiles.sv').write_text(t_)
    cmd = ['iverilog', '-g2012', '-o', str(out / 'sim'), '-s', 'tb_hroot_lockstep', str(out / 'tb.sv'), str(out / 'tiles.sv')] + \
        [str(ROOT / s) for s in srcs] + defs + ['-Y', '.sv'] + \
        [x for d in sorted({str((ROOT / s).parent) for s in srcs}) for x in ('-y', d)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        return 2
    r = subprocess.run(['vvp', '-n', str(out / 'sim')], capture_output=True, text=True)
    print(r.stdout[-2000:])
    ok = 'PASS' in r.stdout
    return 0 if (ok and a.mut == 0) or (not ok and a.mut) else 1


if __name__ == '__main__':
    sys.exit(main())
