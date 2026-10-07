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
    """die port -> {bit: 'out'|'in'} forwarded-clock bits of this master (r16g fwd map; a derived split master
    carries its share of the parent's map in its ports.json 'fclk')."""
    d = V.derived_record(master)
    if d is not None:
        return {p: {int(b): v for b, v in m.items()} for p, m in d.get('fclk', {}).items()}
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


def port_in_stages(spec, p):
    """input-chain depth of die port p: spec 'port_in_stages' overrides port_stages for the input bits of a port"""
    return int(spec.get('port_in_stages', {}).get(p, port_stages(spec, p)))


def port_stages(spec, p):
    """face stages of die port p: spec 'port_stages' {port: N} (owner cost rule 2026-10-06: sized per face from the
    in-view core <-> pin wire, ~one stage per 380-400 um, 2..5), else face_stages."""
    return int(spec.get('port_stages', {}).get(p, spec.get('face_stages', 1)))


def parse_rng(s):
    port, rng = s.split('[')
    lo, hi = rng.rstrip(']').split(':')
    return port, int(lo), int(hi)


def gen(spec):
    master = spec['master']
    rec = V.master_record(master)
    ports = rec['ports']
    fck = fclk_bits(master)
    for p in spec.get('clock_out_ports', []):      # die outputs driven by the (inverted, kept) block clock
        fck.setdefault(p, {}).update({b: 'out' for b in range(ports[p]['bits'])})
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
    L_.append(',\n'.join([f"    {v['direction']} wire [{v['bits'] - 1}:0] {p}" for p, v in sorted(ports.items())]
                          + [f'    /* NOT A GENERATOR PORT (generator-side defect, see note) */ input wire {p}'
                             for p in spec.get('extra_inputs', [])]))
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
            fs = port_in_stages(spec, p)
            if fs == 1:
                L_.append(f'    reg [{v["bits"] - 1}:0] i_{p}; always @(posedge clk) i_{p} <= {p};')
            else:   # face_stages: the pin flop plus fs - 1 further stages toward the consumers
                prev = p
                for k in range(fs - 1):
                    L_.append(f'    reg [{v["bits"] - 1}:0] i{k}_{p}; always @(posedge clk) i{k}_{p} <= {prev};')
                    prev = f'i{k}_{p}'
                L_.append(f'    reg [{v["bits"] - 1}:0] i_{p}; always @(posedge clk) i_{p} <= {prev};')
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
                  for b1 in (b if isinstance(b, list) else [b]):
                    off = 0
                    for part in b1[4:].split('+'):
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
    if folds and spec.get('kept_out_regs'):
        # RTL outputs the die interface does not carry: each bit ends in a kept local sink flop (ot_hfd_sink1) beside
        # its producer, so the logic stays live without the cross-block XOR fold paths
        for f, w in folds:
            L_.append(f'    for (genvar k = 0; k < {w}; k = k + 1) begin : g_sink_{f}')
            L_.append(f'        (* keep *) ot_hfd_sink1 u (.clk(clk), .d({f}[k]), .q());')
            L_.append('    end')
        folds_sunk = True
    elif folds:
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
    # shared-source chain trees (spec 'share_tree': {"min": M, "fanout": F}): an output source bit that feeds >= M face
    # chains is fanned out through kept per-chain-group copies (ot_hfd_oreg1) at the shared chain stages instead of
    # driving M chains from one core flop: level 0 is one copy per die port, every further level splits a group into
    # <= F groups contiguous in bit order (pins of a port are placed in bit order), and each chain keeps its own last
    # stages to the pin.  Every chain still has face_stages flops: cycle-exact, same die latency.
    tree_leaf, tree_lines, tree_stats = {}, [], dict(sources=0, chains=0, nodes=0)
    st = spec.get('share_tree')
    fs = max([port_stages(spec, q) for q in ports] + [spec.get('face_stages', 1)])
    if st and spec.get('kept_out_regs') and fs > 1:
        import re
        src = {}
        for p in sorted(outs):
            for lo, hi, e in outs[p]:
                m = re.fullmatch(r'([A-Za-z_]\w*)\[(\d+):(\d+)\]', e)
                m1 = re.fullmatch(r'([A-Za-z_]\w*)\[(\d+)\]', e)
                for j in range(hi - lo):
                    if m:
                        key = (m.group(1), int(m.group(3)) + j)
                    elif m1 and hi - lo == 1:
                        key = (m1.group(1), int(m1.group(2)))
                    elif re.fullmatch(r'[A-Za-z_]\w*', e) and hi - lo == 1:
                        key = (e, 0)
                    else:
                        continue
                    if key[0].startswith('fold_'):
                        continue
                    src.setdefault(key, []).append((p, lo + j))
        F = st.get('fanout', 4)
        nid = [0]

        def split(ch, level):
            if level == 0:
                g = {}
                for c in ch:
                    g.setdefault(c[0], []).append(c)
                return [g[k] for k in sorted(g)]
            n = min(F, len(ch))
            return [ch[(i * len(ch)) // n:((i + 1) * len(ch)) // n] for i in range(n)]

        def build(ch, level, drv):
            for grp in split(ch, level):
                n = port_stages(spec, grp[0][0])   # level-0 groups are per port, so a group has one depth
                if len(grp) == 1 or level == n - 1:
                    for c in grp:
                        tree_leaf[c] = (n - level, drv, level == 0)
                    continue
                k = nid[0]; nid[0] += 1
                tree_lines.append(f'    wire n_st{k}; (* keep *) ot_hfd_oreg1 u_st{k} (.clk(clk), .d({drv}), .q(n_st{k}));')
                build(grp, level + 1, f'n_st{k}')

        for key in sorted(src):
            ch = sorted(src[key])
            if len(ch) < st.get('min', 3):
                continue
            tree_stats['sources'] += 1
            tree_stats['chains'] += len(ch)
            build(ch, 0, f'{key[0]}[{key[1]}]')
        tree_leaf = {c: v[:2] for c, v in tree_leaf.items() if not v[2]}   # an unshared chain stays a plain chain
        tree_stats['nodes'] = nid[0]
        if tree_lines:
            L_.append(f'    // shared-source chain trees: {tree_stats["sources"]} source bits, {tree_stats["chains"]} chains, '
                      f'{tree_stats["nodes"]} kept group copies')
            L_ += tree_lines
    # output registers
    for p, v in sorted(ports.items()):
        if not any(d == 'out' for d in dirs[p]):
            continue
        if spec.get('kept_out_regs') and tree_leaf:
            segs_d, cur = [], 0
            for lo, hi, e in sorted(outs.get(p, []), key=lambda t: t[0]):
                if lo > cur:
                    segs_d.append(f"{lo - cur}'d0")
                segs_d.append(f'{e}')
                cur = hi
            if cur < v['bits']:
                segs_d.append(f"{v['bits'] - cur}'d0")
            L_.append(f'    wire [{v["bits"] - 1}:0] od_{p} = {{{", ".join(segs_d[::-1])}}};')
            L_.append(f'    wire [{v["bits"] - 1}:0] o_{p};')
            k = 0
            while k < v['bits']:
                if (p, k) in tree_leaf:
                    r, drv = tree_leaf[(p, k)]
                    L_.append(f'    ot_hfd_oreg{r} u_o_{p}_{k} (.clk(clk), .d({drv}), .q(o_{p}[{k}]));')
                    k += 1
                    continue
                j = k
                while j < v['bits'] and (p, j) not in tree_leaf:
                    j += 1
                L_.append(f'    for (genvar k = {k}; k < {j}; k = k + 1) begin : g_o_{p}_{k}')
                L_.append(f'        ot_hfd_oreg{port_stages(spec, p)} u (.clk(clk), .d(od_{p}[k]), .q(o_{p}[k]));')
                L_.append('    end')
                k = j
        elif spec.get('kept_out_regs'):
            # one kept 1-bit flop per die output bit (ot_hfd_oreg1, SYNTH_KEEP_MODULES): yosys would otherwise merge
            # equal-D output flops (a bit broadcast to several quarter ports, or the constant spare bits) into one
            # driver of many far-apart ports
            segs_d, cur = [], 0
            for lo, hi, e in sorted(outs.get(p, []), key=lambda t: t[0]):
                if lo > cur:
                    segs_d.append(f"{lo - cur}'d0")
                segs_d.append(f'{e}')
                cur = hi
            if cur < v['bits']:
                segs_d.append(f"{v['bits'] - cur}'d0")
            L_.append(f'    wire [{v["bits"] - 1}:0] od_{p} = {{{", ".join(segs_d[::-1])}}};')
            L_.append(f'    wire [{v["bits"] - 1}:0] o_{p};')
            L_.append(f'    for (genvar k = 0; k < {v["bits"]}; k = k + 1) begin : g_o_{p}')
            L_.append(f'        ot_hfd_oreg{port_stages(spec, p)} u (.clk(clk), .d(od_{p}[k]), .q(o_{p}[k]));')
            L_.append('    end')
        else:
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
    if tree_lines:
        stats['share_tree'] = tree_stats
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
    if spec.get('port_stages'):
        # per-port chain depth for face_chain_place.tcl (route_view.sh FCF)
        (out / f'{spec["master"]}_face_stages.tcl').write_text(
            '# generated by tools/hbm_die_wrap.py from spec port_stages: die port -> face chain depth\n'
            + ''.join(f'set fc_ps({p}) {n}\n' for p, n in sorted(spec['port_stages'].items()))
            + ''.join(f'set fc_psi({p}) {n}\n' for p, n in sorted(spec.get('port_in_stages', {}).items())))
    print(json.dumps({k: v for k, v in st.items() if k != 'cfg_inputs'}))




def gen_tb(spec, cycles=400, seed=20261006):
    """Lockstep bench: the wrapper against the same unchanged RTL instance(s) driven straight from the stimulus.
    Die-bound inputs of the reference are the die input bits delayed one cycle (the wrapper's input register); every
    other reference input (clock, reset, cfg chain, wrapper expressions) is the wrapper's own internal wire.  Every
    die-bound output bit must equal the reference output one cycle later (the wrapper's output register).  One seed;
    $fatal (nonzero exit) on any mismatch."""
    master = spec['master']
    rec = V.master_record(master)
    ports = rec['ports']
    T = [f'`timescale 1ns/1ps', f'// lockstep bench of {master} (tools/hbm_die_wrap.py --tb): one seed {seed}', f'module tb_{master};']
    for p, v in sorted(ports.items()):
        kind = v['direction']
        T.append(f'    {"reg" if kind == "input" else "wire"} [{v["bits"] - 1}:0] {p};')
        if kind == 'inout':
            T.append(f'    reg [{v["bits"] - 1}:0] drv_{p};')
    xin = spec.get('extra_inputs', [])
    for p in xin:
        T.append(f'    reg {p};')
    conn = ', '.join([f'.{p}({p})' for p in sorted(ports)] + [f'.{p}({p})' for p in xin])
    T.append(f'    {master} dut({conn});')
    # inout drive: drive only the input bits
    dirs = {}
    for p, v in ports.items():
        arr = ['in'] * v['bits']
        for a, b, d in v['dir_segments']:
            for i in range(a, b):
                arr[i] = 'out' if d == 'out' else 'in'
        dirs[p] = arr
        if v['direction'] == 'inout':
            for i, d in enumerate(arr):
                if d == 'in':
                    T.append(f"    assign {p}[{i}] = drv_{p}[{i}];")
    T.append('    reg clk = 0; always #0.4165 clk = ~clk;')
    T.append('    always @* ck[0] = clk;' if 'ck' in ports else '')
    if spec.get('clock') in xin:
        T.append(f"    always @* {spec['clock']} = clk;")
    # one-cycle delayed copies of every input-capable port
    for p, v in sorted(ports.items()):
        if v['direction'] != 'output':
            src = f'drv_{p}' if v['direction'] == 'inout' else p
            for k in range(port_in_stages(spec, p) - 1):
                T.append(f'    reg [{v["bits"] - 1}:0] d{k}_{p}; always @(posedge clk) d{k}_{p} <= {src};')
                src = f'd{k}_{p}'
            T.append(f'    reg [{v["bits"] - 1}:0] d_{p}; always @(posedge clk) d_{p} <= {src};')
    checks = []
    for inst in spec['instances']:
        pm = L.parse_module(inst['file'], inst['module'], inst.get('params'))['ports']
        conns = []
        for rp, (rd, rw) in pm.items():
            b = inst['bind'].get(rp, 'cfg' if rd == 'input' else 'fold')
            w = f'r_{inst["name"]}_{rp}'
            T.append(f'    wire [{rw - 1}:0] {w};')
            conns.append(f'.{rp}({w})')
            if rd == 'input':
                if isinstance(b, str) and b.startswith('die:'):
                    srcs = []
                    n = 0
                    for part in b[4:].split('+'):
                        port, lo, hi = parse_rng(part)
                        srcs.append(f'd_{port}[{hi - 1}:{lo}]')
                        n += hi - lo
                    srcs = srcs[::-1]
                    if n < rw:
                        srcs = [f"{rw - n}'d0"] + srcs
                    T.append(f'    assign {w} = {{{", ".join(srcs)}}};')
                else:
                    T.append(f'    assign {w} = dut.w_{inst["name"]}_{rp};')
            else:
                for b1 in (b if isinstance(b, list) else [b]):
                    if not (isinstance(b1, str) and b1.startswith('die:')):
                        continue
                    off = 0
                    for part in b1[4:].split('+'):
                        port, lo, hi = parse_rng(part)
                        n = min(hi - lo, rw - off)
                        checks.append((f'{port}[{lo + n - 1}:{lo}]', f'q{port_stages(spec, port)}_{inst["name"]}_{rp}[{off + n - 1}:{off}]'))
                        off += n
                # reference output delayed 1..max port stages (each die port checked at its own depth)
                src = w
                for k in range(1, max([port_stages(spec, q) for q in ports] + [1]) + 1):
                    T.append(f'    reg [{rw - 1}:0] q{k}_{inst["name"]}_{rp}; always @(posedge clk) q{k}_{inst["name"]}_{rp} <= {src};')
                    src = f'q{k}_{inst["name"]}_{rp}'
        prm = ', '.join(f'.{k}({v})' for k, v in inst.get('params', {}).items())
        T.append(f'    {inst["module"]} {"#(" + prm + ") " if prm else ""}ref_{inst["name"]} ({", ".join(conns)});')
    T += ['    integer err = 0, nchk = 0, cyc;', f'    integer seed = {seed};',
          '    task automatic randomize_inputs; begin']
    for p, v in sorted(ports.items()):
        if p == 'ck' or v['direction'] == 'output':
            continue
        tgt = f'drv_{p}' if v['direction'] == 'inout' else p
        if p == 'rst':
            continue
        for k in range(0, v['bits'], 32):
            hi = min(v['bits'], k + 32)
            T.append(f'        {tgt}[{hi - 1}:{k}] = $urandom(seed); seed = seed + 1;')
    T += ['    end endtask', '    initial begin']
    rstp = 'rst' if 'rst' in ports else spec.get('rst') if spec.get('rst') in xin else None
    if rstp:
        T.append(f"        {rstp} = 1;")
    T += ['        randomize_inputs;', '        repeat (8) @(posedge clk);']
    if rstp:
        T.append(f"        #0.05 {rstp} = 0;")
    T += [f'        for (cyc = 0; cyc < {cycles}; cyc = cyc + 1) begin', '            @(negedge clk);']
    for a, b in checks:
        T.append(f'            nchk = nchk + 1; if ({a} !== {b}) begin err = err + 1; '
                 f'if (err < 10) $display("MISMATCH {a} %h ref %h cyc %0d", {a}, {b}, cyc); end')
    T += ['            randomize_inputs;', '        end',
          f'        $display("TB_{master} checks=%0d mismatches=%0d", nchk, err);',
          '        if (err != 0 || nchk == 0) $fatal(1, "FAIL");', '        $finish;', '    end', 'endmodule']
    return '\n'.join(T) + '\n'


def main_tb():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--cycles', type=int, default=400)
    a = ap.parse_args(sys.argv[2:])
    spec = json.loads(Path(a.spec).read_text())
    out = Path(a.out)
    (out / f'tb_{spec["master"]}.sv').write_text(gen_tb(spec, a.cycles))
    print(f'tb_{spec["master"]}.sv')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--tb':
        main_tb()
    else:
        main()
