#!/usr/bin/env python3
"""Thin registered die wrappers for the HBM accelerator DS die views (CLAUDE HBM-ABSTRACTS, spine, 2026-10-06).

A wrapper is a module named as the r16g generator master with EXACTLY the master's die ports (names, widths,
per-bit directions from tools/hbm_die_views.py).  It registers every die input bit once (ck), drives every die output
bit from a register, and binds the unchanged RTL block(s) inside by an explicit per-port mapping:

    'die:PORT[lo:hi]'    registered die input bits lo..hi-1 (inputs) / die output bits (outputs)
    'const:V'            a constant input
    'cfg'                a bit of the wrapper's configuration shift chain (an input the die interface does not
                         carry: loaded serially from one spare die input bit, so the logic behind it stays live)
    'fold'               an RTL output the die interface does not carry: XOR-folded into the spare die output bits
    'clk' / 'rst_n'      the die clock / the synchronised active-low reset (die rst is active high, 2-flop synced)

Forwarded clocks: die output bits that are a segment's forwarded clock (the generator's fclk map, one per 512 b slice
and direction) are driven by the die clock through a kept ot_fwd_clk_inv; incoming forwarded clocks are captured as
data (the receiving meso FIFO of the block is modelled as a ck-domain capture: interim).

    python3 tools/hbm_die_wrap.py --kind barrier --out physical/hbm_accel_die_views/barrier/rtl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_die_views as V  # noqa: E402

L = V.L


def fclk_bits(master):
    """die port -> {bit: 'out'|'in'} forwarded-clock bits of this master (r16g fwd map)."""
    m, pw, M, real = V.model()
    by = {it.name: it for it in m['insts']}
    out = {}
    for bid, cls, bits, eps in m['buses']:
        fc = m.get('fclk', {}).get(bid)
        if not fc:
            continue
        base, nd, nu = fc
        for j, (inst, port) in enumerate(eps):
            if inst == 'TOP' or by[inst].master != master:
                continue
            d = out.setdefault(port, {})
            for b in range(base, base + nd):
                d[b] = 'out' if j == 0 else 'in'
            for b in range(base + nd, base + nd + nu):
                d[b] = 'in' if j == 0 else 'out'
    return out


def parse_rng(s):
    port, rng = s.split('[')
    lo, hi = rng.rstrip(']').split(':')
    return port, int(lo), int(hi)


def gen(spec):
    master = spec['master']
    rec = V.master_record(master)
    ports = rec['ports']
    fck = fclk_bits(master)
    dirs = {}
    for p, v in ports.items():
        arr = ['in'] * v['bits']
        for a, b, d in v['dir_segments']:
            for i in range(a, b):
                arr[i] = 'out' if d == 'out' else 'in'
        dirs[p] = arr
    used_in = {p: [False] * v['bits'] for p, v in ports.items()}
    used_out = {p: [False] * v['bits'] for p, v in ports.items()}
    for p, d in fck.items():
        for b, dd in d.items():
            if dd == 'out':
                used_out[p][b] = True
    L_ = [f'// {master}: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).',
          f'// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing',
          f'// instantiates it except the die view route.  {spec.get("note", "")}',
          f'module {master} (']
    L_.append(',\n'.join(f"    {v['direction']} wire [{v['bits'] - 1}:0] {p}" for p, v in sorted(ports.items())))
    L_.append(');')
    ck = spec.get('clock', 'ck[0]')
    L_ += [f'    wire clk = {ck};',
           f'    reg [1:0] rst_s; always @(posedge clk) rst_s <= {{rst_s[0], {spec.get("rst", "rst[0]")}}};',
           '    wire rst_n = ~rst_s[1];']
    # registered die inputs (input bits of every port)
    for p, v in sorted(ports.items()):
        if p in ('ck',) or (p == 'rst' and spec.get('rst', 'rst[0]') == 'rst[0]'):
            continue
        if any(d == 'in' for d in dirs[p]):
            L_.append(f'    reg [{v["bits"] - 1}:0] i_{p}; always @(posedge clk) i_{p} <= {p};')
    sigs, outs, ncfg, folds = [], {}, 0, []
    cfg_bits = []
    body = []
    for inst in spec['instances']:
        pm = L.parse_module(inst['file'], inst['module'], inst.get('params'))['ports']
        conns = []
        for rp, (rd, rw) in pm.items():
            b = inst['bind'].get(rp, 'cfg' if rd == 'input' else 'fold')
            w = f'w_{inst["name"]}_{rp}'
            sigs.append(f'    wire [{rw - 1}:0] {w};')
            conns.append(f'.{rp}({w})')
            if rd == 'input':
                if b == 'clk':
                    body.append(f'    assign {w} = {{{rw}{{clk}}}};')
                elif b == 'rst_n':
                    body.append(f'    assign {w} = {{{rw}{{rst_n}}}};')
                elif b.startswith('const:'):
                    body.append(f"    assign {w} = {rw}'d{b[6:]};")
                elif b == 'cfg':
                    body.append(f'    assign {w} = cfg[{ncfg + rw - 1}:{ncfg}];')
                    cfg_bits.append((inst['name'], rp, rw))
                    ncfg += rw
                elif b.startswith('expr:'):
                    body.append(f'    assign {w} = {b[5:]};')
                else:
                    srcs = []
                    for part in b[4:].split('+'):
                        port, lo, hi = parse_rng(part)
                        for i in range(lo, hi):
                            assert dirs[port][i] == 'in', (master, port, i, 'not an input bit')
                            used_in[port][i] = True
                        srcs.append(f'i_{port}[{hi - 1}:{lo}]')
                    n = sum(parse_rng(x)[2] - parse_rng(x)[1] for x in b[4:].split('+'))
                    srcs = srcs[::-1]
                    if n < rw:
                        srcs = [f"{rw - n}'d0"] + srcs
                    assert n <= rw, (inst['name'], rp, n, rw)
                    body.append(f'    assign {w} = {{{", ".join(srcs)}}};')
            else:
                if b == 'fold':
                    folds.append((w, rw))
                elif b == 'open':
                    pass
                else:
                    off = 0
                    for part in b[4:].split('+'):
                        port, lo, hi = parse_rng(part)
                        n = min(hi - lo, rw - off)
                        for i in range(lo, lo + n):
                            assert dirs[port][i] == 'out', (master, port, i, 'not an output bit')
                            assert not used_out[port][i], (master, port, i, 'driven twice')
                            used_out[port][i] = True
                        outs.setdefault(port, []).append((lo, lo + n, f'{w}[{off + n - 1}:{off}]'))
                        off += n
        prm = ', '.join(f'.{k}({v})' for k, v in inst.get('params', {}).items())
        body.append(f'    {inst["module"]} {"#(" + prm + ") " if prm else ""}u_{inst["name"]} ({", ".join(conns)});')
    # extra wrapper logic (verbatim) may drive die output bits via spec['extra_out']: [(port, lo, hi, expr)]
    for port, lo, hi, expr in spec.get('extra_out', []):
        for i in range(lo, hi):
            assert dirs[port][i] == 'out' and not used_out[port][i], (port, i)
            used_out[port][i] = True
        outs.setdefault(port, []).append((lo, hi, expr))
    body = spec.get('extra', []) + body
    # spare bits
    spare_in = [(p, i) for p in sorted(ports) if p not in ('ck', 'rst') for i, d in enumerate(dirs[p])
                if d == 'in' and not used_in[p][i] and not (p in fck and i in fck[p])]
    spare_out = [(p, i) for p in sorted(ports) for i, d in enumerate(dirs[p]) if d == 'out' and not used_out[p][i]]
    L_ += sigs
    if ncfg:
        if not spare_in:
            raise SystemExit(f'{master}: {ncfg} cfg bits but no spare die input bit')
        sp, si = spare_in.pop(0)
        L_.append(f'    // configuration chain: {ncfg} RTL input bits the die interface does not carry, shifted from '
                  f'die input {sp}[{si}]')
        L_.append(f'    reg [{ncfg - 1}:0] cfg; always @(posedge clk) cfg <= {{cfg[{max(ncfg - 2, 0)}:0], i_{sp}[{si}]}};'
                  if ncfg > 1 else f'    reg [0:0] cfg; always @(posedge clk) cfg <= i_{sp}[{si}];')
    L_ += body
    # fold
    fold_assign = []
    if folds:
        tot = sum(w for _, w in folds)
        allbits = ' ,'.join(f for f, _ in folds[::-1])
        L_.append(f'    wire [{tot - 1}:0] fold_all = {{{allbits}}};')
        nsp = min(len(spare_out), max(1, (tot + 63) // 64))
        if not spare_out:
            raise SystemExit(f'{master}: {tot} folded output bits but no spare die output bit')
        for k in range(nsp):
            p, i = spare_out.pop(0)
            idx = [j for j in range(k, tot, nsp)]
            L_.append(f'    wire fold_{k} = ^{{{", ".join(f"fold_all[{j}]" for j in idx)}}};')
            outs.setdefault(p, []).append((i, i + 1, f'fold_{k}'))
            used_out[p][i] = True
    # forwarded clocks out
    fwd = [(p, b) for p, d in sorted(fck.items()) for b, dd in sorted(d.items()) if dd == 'out']
    for k, (p, b) in enumerate(fwd):
        L_.append(f'    wire fclk_{k}; ot_fwd_clk_inv u_fclk_{k} (.a(clk), .y(fclk_{k}));')
    # output registers
    for p, v in sorted(ports.items()):
        if not any(d == 'out' for d in dirs[p]):
            continue
        L_.append(f'    reg [{v["bits"] - 1}:0] o_{p};')
        L_.append(f'    always @(posedge clk) begin')
        L_.append(f"        o_{p} <= {v['bits']}'d0;")
        for lo, hi, e in outs.get(p, []):
            L_.append(f'        o_{p}[{hi - 1}:{lo}] <= {e};')
        L_.append('    end')
        segs = []
        i = 0
        arr = dirs[p]
        while i < len(arr):
            if arr[i] == 'out':
                j = i
                while j < len(arr) and arr[j] == 'out':
                    j += 1
                segs.append((i, j))
                i = j
            else:
                i += 1
        for a, b in segs:
            fwd_here = [k for k, (pp, bb) in enumerate(fwd) if pp == p and a <= bb < b]
            if not fwd_here:
                L_.append(f'    assign {p}[{b - 1}:{a}] = o_{p}[{b - 1}:{a}];')
            else:
                for i2 in range(a, b):
                    kk = [k for k, (pp, bb) in enumerate(fwd) if pp == p and bb == i2]
                    L_.append(f'    assign {p}[{i2}] = ' + (f'fclk_{kk[0]};' if kk else f'o_{p}[{i2}];'))
    L_.append('endmodule')
    stats = dict(master=master, cfg_bits=ncfg, cfg_inputs=cfg_bits, folded_output_bits=sum(w for _, w in folds),
                 folded_outputs=[f for f, _ in folds], forwarded_clock_outputs=len(fwd),
                 forwarded_clock_inputs=sum(1 for d in fck.values() for dd in d.values() if dd == 'in'),
                 die_input_bits=sum(d == 'in' for p in dirs for d in dirs[p]),
                 die_input_bits_used=sum(sum(u) for u in used_in.values()),
                 die_output_bits=sum(d == 'out' for p in dirs for d in dirs[p]),
                 die_output_bits_driven=sum(sum(u) for u in used_out.values()))
    return '\n'.join(L_) + '\n', stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', required=True, help='JSON spec file')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    sv, st = gen(spec)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f'{spec["master"]}.sv').write_text(sv)
    (out / f'{spec["master"]}_wrap.json').write_text(json.dumps(st, indent=1) + '\n')
    print(json.dumps({k: v for k, v in st.items() if k != 'cfg_inputs'}))


if __name__ == '__main__':
    main()
