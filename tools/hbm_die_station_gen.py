#!/usr/bin/env python3
"""HBM accelerator DS die (r16g): ONE parameterised forwarded-link station design, emitted per station master
(CLAUDE HBM-ABSTRACTS stations, 2026-10-06).

Every station master of tools/hbm_accel_die_fp.py (hfd_stn_r*, hfd_meso_r*, hfd_mcast_r*, hfd_gath_r*, hfd_cdist_r*)
gets a top module named as the master with exactly the generator's ports (tools/hbm_die_views.py ports.json), built
from three primitives in physical/hbm_accel_die_views/stations/rtl/ot_hbm_stn_lib.sv:

  ot_hbm_stn_fwd     forwarded pass-through slice: rtl/common/ot_fwd_link_stage (ENABLE=1): capture on the falling
                     edge of the incoming forwarded clock, forward the clock through the kept inverter
  ot_hbm_stn_launch  start a forwarded slice from the local clock ck: posedge registers, forwarded clock = ck through
                     two kept inverters (data launched at the forwarded clock's rising edge, like a pass-through)
  ot_hbm_stn_meso    terminate a forwarded slice into ck: kept inverter (write on the forwarded clock's falling edge)
                     + rtl/common/ot_meso_fifo W<=512 D4 (ENABLE=1, no backpressure: w_v = r_rdy = 1)

BIT-PACKING CONVENTION (every forwarded segment; the generator's bit counts): a segment port of fc = (base, nd, nu)
carries data bits [0, base) in the generator's per-bit directions (DIRECTION MODEL), then nd downstream forwarded
clocks at [base, base + nd), then nu upstream forwarded clocks at [base + nd, base + nd + nu).  The downstream data
bits, in ascending index order, are cut into slices of 512: slice k is clocked by forwarded clock base + k.  The
upstream data bits likewise: slice k by clock base + nd + k.  A station maps data bit i of one port to data bit i of
the other (same index) unless its role says otherwise (below).  Downstream capture: falling edge of the received
forwarded clock; every launch is on the rising edge of the forwarded clock it sends.

Role maps (data index conventions the endpoint owners adopt):
  gath   b data = {a2 (meso'd), a, t1, t0} from bit 0 up: t0 [0, 270), t1 [270, 540), a [540, 1080), a2 [1080, 2160)
  cdist  a / b are 103-bit control leaves; leaves 0-3 of a are the taps t0-t3, leaves 4-7 of a are leaves 0-3 of b
  launch (weight request, SM side): a[42:0] -> b[42:0]; a[43] (SM req_ready) is driven 1 (no ready return in the
         generator), b[43] is driven 0
Reset 'rst' is active low (rst_n), quasi-static: it resets the meso crossings and launch registers.

Modes: emit --ports DIR --out DIR [--master M ...]   (DIR from tools/hbm_die_views.py ports)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

SL = 512
T_PS = 833.333
IOD = 166.666          # 0.2 T io budget, as route_view.sh


def fc_map():
    """(master, port) -> (base, nd, nu) of the forwarded segments the port carries (None: local / unforwarded)."""
    import hbm_die_views as V
    m, pw, M, real = V.model()
    by = {it.name: it for it in m['insts']}
    fc = m.get('fclk', {})
    out = {}
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            if inst == 'TOP':
                continue
            mst = by[inst].master
            if V.kind_of(mst) != 'stations':
                continue
            k = (mst, port)
            v = fc.get(bid)
            v = tuple(v) if v else None
            if k in out and out[k] != v:
                raise SystemExit(f'{mst}.{port}: inconsistent forwarded layout {out[k]} vs {v}')
            out[k] = v
    return out


def dirs(rec, port):
    """per-bit direction list of a port ('in' / 'out')."""
    p = rec['ports'][port]
    arr = ['?'] * p['bits']
    for a, b, d in p['dir_segments']:
        for i in range(a, b):
            arr[i] = d
    if p['direction'] == 'input':
        arr = ['in'] * p['bits']
    elif p['direction'] == 'output':
        arr = ['out'] * p['bits']
    return arr


def rng(bits):
    """compact concatenation of single bits [(port, idx)] (MSB first for Verilog)."""
    parts = []
    for port, i in reversed(bits):
        if parts and parts[-1][0] == port and parts[-1][2] == i + 1:
            parts[-1][2] = i
        else:
            parts.append([port, i, i])
    s = []
    for port, hi, lo in parts:
        s.append(f'{port}[{hi}]' if hi == lo else f'{port}[{hi}:{lo}]')
    return '{' + ', '.join(s) + '}' if len(s) > 1 else s[0]


class Emit:
    def __init__(self, rec, fcm, mutant=False, margin=False):
        self.rec, self.fcm, self.n = rec, fcm, 0
        self.margin = margin          # owner margin rule: register every face pin of a meso crossing (see --margin)
        self.body, self.sdc, self.map = [], [], {}
        self.clk_in, self.clk_out = [], []        # (port, idx) forwarded clock inputs / outputs
        self.mutant = mutant          # negative control: the first primitive swaps its two lowest data bits
        self.ck = 'ck' in rec['ports']
        self.ins = {}                             # (port, idx) -> domain clock name of input data
        self.outs = {}                            # (port, idx) -> ('fwd', out clock port bit) | ('ck',)

    def mut(self, lst):
        if self.mutant and len(lst) >= 2:
            lst = list(lst)
            lst[0], lst[1] = lst[1], lst[0]
            self.mutant = False
        return lst

    def name(self, s):
        self.n += 1
        return f'u_{s}{self.n}'

    def layout(self, port):
        fc = self.fcm.get((self.rec['master'], port))
        d = dirs(self.rec, port)
        if not fc:
            return None, d
        base, nd, nu = fc
        return fc, d

    def slices(self, port, want):
        """data bits of a forwarded port in direction want ('in'/'out' at this port), cut in slices of 512, with the
        forwarded clock bit of each slice."""
        fc, d = self.layout(port)
        base, nd, nu = fc
        down = (want == 'in') == self.is_up_side(port)    # downstream data enters at the upstream-side port
        bits = [i for i in range(base) if d[i] == want]
        ns = (len(bits) + SL - 1) // SL
        clk0 = base if down else base + nd
        nclk = nd if down else nu
        assert ns == nclk, (self.rec['master'], port, want, len(bits), ns, nclk, fc)
        return [(bits[k * SL:(k + 1) * SL], clk0 + k) for k in range(ns)]

    def is_up_side(self, port):
        """the port that faces upstream (receives the downstream data): a / a2 (generator: chain src -> (st, 'a'))."""
        return port in ('a', 'a2')

    # ---------------------------------------------------------------- primitives
    def fwd(self, ip, ibits, iclk, op, obits, oclk):
        u = self.name('fwd')
        w = len(ibits)
        src = self.mut([(ip, i) for i in ibits])
        self.body.append(f'  ot_hbm_stn_fwd #(.W({w})) {u} (.fclk_i({ip}[{iclk}]), .d_i({rng(src)}), '
                         f'.fclk_o({op}[{oclk}]), .d_o({rng([(op, i) for i in obits])}));')
        self.clk_in.append((ip, iclk))
        self.clk_out.append(((op, oclk), (ip, iclk), True))
        for a, b in zip(ibits, obits):
            self.map[f'{op}[{b}]'] = dict(src=f'{ip}[{a}]', dom=f'{op}[{oclk}]')
            self.ins[(ip, a)] = (ip, iclk)
            self.outs[(op, b)] = ('fwd', (op, oclk))

    def meso(self, ip, ibits, iclk, tag):
        """forwarded slice -> ck domain wire vector; returns the wire name."""
        u = self.name('meso')
        w = len(ibits)
        wn = f'm_{u}'
        self.body.append(f'  wire [{w - 1}:0] {wn};')
        ri = ', .RI(1), .RDREG(1), .NOBP(1), .CRDREG(1), .OBYP(1)' if self.margin else ''
        self.body.append(f'  ot_hbm_stn_meso #(.W({w}){ri}) {u} (.fclk_i({ip}[{iclk}]), .d_i({rng(self.mut([(ip, i) for i in ibits]))}), '
                         f'.ck(ck[0]), .rst_n(rst[0]), .d_o({wn}));')
        self.clk_in.append((ip, iclk))
        for i in ibits:
            self.ins[(ip, i)] = (ip, iclk)
        return wn, [f'{ip}[{i}]' for i in ibits]

    def launch(self, srcs, op, obits, oclk):
        """srcs: list of verilog bit expressions (ck domain) -> forwarded slice out on op[obits], clock op[oclk]."""
        u = self.name('lau')
        w = len(obits)
        self.body.append(f'  ot_hbm_stn_launch #(.W({w})) {u} (.ck(ck[0]), .d_i({{{", ".join(reversed(self.mut(srcs)))}}}), '
                         f'.fclk_o({op}[{oclk}]), .d_o({rng([(op, i) for i in obits])}));')
        self.clk_out.append(((op, oclk), ('ck', 0), False))
        for s, b in zip(srcs, obits):
            self.map[f'{op}[{b}]'] = dict(src=s, dom=f'{op}[{oclk}]')
            self.outs[(op, b)] = ('fwd', (op, oclk))

    def local(self, srcs, op, obits):
        """ck-domain registered outputs (or direct from a meso output register)."""
        for s, b in zip(srcs, obits):
            self.map[f'{op}[{b}]'] = dict(src=s, dom='ck')
            self.outs[(op, b)] = ('ck',)

    def drive(self, op, obits, src):
        """--margin: ck-domain output bits op[obits] from the wire bit expressions src through a register of their own
        at this port (a FIFO output that feeds two faces gets one copy per face)."""
        u = self.name('pin')
        w = len(obits)
        self.body.append(f'  reg [{w - 1}:0] {u}; always @(posedge ck[0]) {u} <= {{{", ".join(reversed(src))}}};')
        for j, b in enumerate(obits):
            self.body.append(f'  assign {op}[{b}] = {u}[{j}];')

    def reg(self, srcs, tag):
        """register ck-domain inputs once; returns the list of register bit expressions."""
        u = self.name('reg')
        w = len(srcs)
        self.body.append(f'  reg [{w - 1}:0] {u}; always @(posedge ck[0]) {u} <= {{{", ".join(reversed(self.mut(srcs)))}}};')
        return [f'{u}[{i}]' for i in range(w)]


def build(rec, fcm, mutant=False, margin=False):
    E = Emit(rec, fcm, mutant, margin)
    mst = rec['master']
    role = mst.split('_')[1]
    P = rec['ports']
    has = lambda p: p in P  # noqa: E731
    lay = {p: E.layout(p) for p in P if p not in ('ck', 'rst')}

    def plain_dir(ip, op, want_in):
        for (ib, ic), (ob, oc) in zip(E.slices(ip, 'in'), E.slices(op, 'out')):
            assert ib == ob, (mst, ip, op)
            E.fwd(ip, ib, ic, op, ob, oc)

    if role == 'stn' and lay['a'][0] and lay['b'][0]:
        plain_dir('a', 'b', True)                 # downstream
        if lay['a'][0][2]:
            plain_dir('b', 'a', False)            # upstream
        rl = 'forward'
    elif role == 'stn':                           # launch: a local (SM request), b forwarded
        da = dirs(rec, 'a')
        assert not lay['a'][0] and lay['b'][0]
        (ob, oc), = E.slices('b', 'out')
        ain = [i for i, d in enumerate(da) if d == 'in']
        aout = [i for i, d in enumerate(da) if d == 'out']
        srcs = [f'a[{i}]' for i in ain] + ["1'b0"] * (len(ob) - len(ain))
        for i in ain:
            E.ins[('a', i)] = ('ck', 0)
        E.launch(srcs, 'b', ob, oc)
        for i in aout:
            E.body.append(f'  reg r_one_{i}; always @(posedge ck[0]) r_one_{i} <= rst[0];  // SM req_ready: no ready return')
            E.body.append(f'  assign a[{i}] = r_one_{i};')
            E.map[f'a[{i}]'] = dict(src='rst', dom='ck')
            E.outs[('a', i)] = ('ck',)
        rl = 'launch'
    elif role == 'meso':
        db = dirs(rec, 'b')
        for ib, ic in E.slices('a', 'in'):
            wn, srcs = E.meso('a', ib, ic, 'down')
            if E.margin:
                E.drive('b', ib, [f'{wn}[{j}]' for j in range(len(ib))])
            else:
                E.body.append(f'  assign {rng([("b", i) for i in ib])} = {wn};')
            E.local(srcs, 'b', ib)
        if lay['a'][0][2]:
            for ob, oc in E.slices('a', 'out'):
                assert all(db[i] == 'in' for i in ob)
                for i in ob:
                    E.ins[('b', i)] = ('ck', 0)
                E.launch(E.reg([f'b[{i}]' for i in ob], 'up'), 'a', ob, oc)
                for i, b in zip(ob, ob):
                    E.map[f'a[{b}]']['src'] = f'b[{i}]'
        rl = 'meso'
    elif role == 'mcast':
        for ib, ic in E.slices('a', 'in'):
            if has('b'):
                ob, oc = next((o, c) for o, c in E.slices('b', 'out') if o == ib)
                E.fwd('a', ib, ic, 'b', ob, oc)
            wn, srcs = E.meso('a', ib, ic, 'tap')
            for t in ('t0', 't1'):
                if E.margin:
                    E.drive(t, ib, [f'{wn}[{j}]' for j in range(len(ib))])
                else:
                    E.body.append(f'  assign {rng([(t, i) for i in ib])} = {wn};')
                E.local(srcs, t, ib)
        rl = 'mcast'
    elif role == 'gath':
        srcs = []
        for t in ('t0', 't1'):
            srcs += [f'{t}[{i}]' for i in range(P[t]['bits'])]
            for i in range(P[t]['bits']):
                E.ins[(t, i)] = ('ck', 0)
        if has('a'):
            srcs += [f'a[{i}]' for i in range(P['a']['bits'])]
            for i in range(P['a']['bits']):
                E.ins[('a', i)] = ('ck', 0)
        if has('a2'):
            for ib, ic in E.slices('a2', 'in'):
                wn, _ = E.meso('a2', ib, ic, 'a2')
                srcs += [f'{wn}[{j}]' for j in range(len(ib))]
                for j, i in enumerate(ib):
                    E.map.setdefault('_alias', {})[f'{wn}[{j}]'] = f'a2[{i}]'
        if lay['b'][0]:
            regs = E.reg(srcs, 'gath')
            pos = 0
            for ob, oc in E.slices('b', 'out'):
                E.launch(regs[pos:pos + len(ob)], 'b', ob, oc)
                for k, b in enumerate(ob):
                    s = srcs[pos + k]
                    E.map[f'b[{b}]']['src'] = E.map.get('_alias', {}).get(s, s)
                pos += len(ob)
            assert pos == len(srcs), (mst, pos, len(srcs))
        else:
            regs = E.reg(srcs, 'gath')
            E.body.append(f'  assign b = {{{", ".join(reversed(regs))}}};')
            E.local(srcs, 'b', list(range(len(srcs))))
        rl = 'gather'
    elif role == 'cdist':
        W = 103
        da = dirs(rec, 'a')
        nleaf_a = (lay['a'][0][0]) // W
        # downstream: a -> meso -> ck
        down = {}
        for ib, ic in E.slices('a', 'in'):
            wn, srcs = E.meso('a', ib, ic, 'down')
            for j, i in enumerate(ib):
                down[i] = (f'{wn}[{j}]', f'a[{i}]')
        up_b = {}
        if has('b'):
            for ib, ic in E.slices('b', 'in'):
                wn, srcs = E.meso('b', ib, ic, 'up')
                for j, i in enumerate(ib):
                    up_b[i] = (f'{wn}[{j}]', f'b[{i}]')
        # taps: leaves 0-3
        for t in range(4):
            tp = f't{t}'
            dt = dirs(rec, tp)
            tob = []
            for i in range(W):
                ai = t * W + i
                assert (dt[i] == 'out') == (da[ai] == 'in'), (mst, tp, i)
                if dt[i] == 'out':
                    tob.append(i)
                    E.local([down[ai][1]], tp, [i])
                else:
                    E.ins[(tp, i)] = ('ck', 0)
            if tob:
                if E.margin:
                    E.drive(tp, tob, [down[t * W + i][0] for i in tob])
                else:
                    for i in tob:
                        E.body.append(f'  assign {tp}[{i}] = {down[t * W + i][0]};')
        # b downstream: leaves 4.. of a
        if has('b'):
            for ob, oc in E.slices('b', 'out'):
                srcs = [down[4 * W + i] for i in ob]
                E.launch([s[0] for s in srcs], 'b', ob, oc)
                for s, b in zip(srcs, ob):
                    E.map[f'b[{b}]']['src'] = s[1]
        # a upstream: taps' up bits (leaves 0-3) and b's up bits (leaves 4..)
        for ob, oc in E.slices('a', 'out'):
            srcs, names = [], []
            for i in ob:
                leaf, k = divmod(i, W)
                if leaf < 4:
                    srcs.append(f't{leaf}[{k}]'); names.append(f't{leaf}[{k}]')
                else:
                    s = up_b[(leaf - 4) * W + k]
                    srcs.append(s[0]); names.append(s[1])
            E.launch(E.reg(srcs, 'up'), 'a', ob, oc)
            for n_, b in zip(names, ob):
                E.map[f'a[{b}]']['src'] = n_
        rl = 'cdist'
    else:
        raise SystemExit(f'no role for {mst}')
    E.map.pop('_alias', None)
    return E, rl


def module_text(rec, E):
    decl = ',\n'.join(f"    {v['direction']} wire [{v['bits'] - 1}:0] {p}" for p, v in sorted(rec['ports'].items()))
    return (f"// {rec['master']}: CLAUDE HBM-ABSTRACTS station view (tools/hbm_die_station_gen.py; ports = r16g generator "
            f"master, tools/hbm_die_views.py)\nmodule {rec['master']} (\n{decl}\n);\n" + '\n'.join(E.body) + '\nendmodule\n')


def sim_text(rec, E, name):
    """bench-only shim (Verilator has no partial-bit inout drivers): the same body behind split ports, every inout
    port p as input p_i / output p_o around an internal wire p (inputs assigned bit by bit into p)."""
    decl, pre = [], []
    for p, v in sorted(rec['ports'].items()):
        w = v['bits']
        if v['direction'] != 'inout':
            decl.append(f"    {v['direction']} wire [{w - 1}:0] {p}")
            continue
        decl += [f'    input wire [{w - 1}:0] {p}_i', f'    output wire [{w - 1}:0] {p}_o']
        pre.append(f'  wire [{w - 1}:0] {p};')
        ins = [i for i, d in enumerate(dirs(rec, p)) if d == 'in']
        i = 0
        while i < len(ins):
            j = i
            while j + 1 < len(ins) and ins[j + 1] == ins[j] + 1:
                j += 1
            pre.append(f'  assign {p}[{ins[j]}:{ins[i]}] = {p}_i[{ins[j]}:{ins[i]}];')
            i = j + 1
        pre.append(f'  assign {p}_o = {p};')
    return (f"// bench shim of {rec['master']} (split inout ports; body identical)\nmodule {name} (\n" + ',\n'.join(decl)
            + '\n);\n' + '\n'.join(pre + E.body) + '\nendmodule\n')


def sdc_text(rec, E):
    L = [f"# {rec['master']}: forwarded clocks (one per 512 b slice and direction), the local clock ck, the meso",
         '# crossings (max 356.667 / min 0 ps ignoring latency, the closed ot_meso_fifo W512 D4 contract), io budget 0.2 T.',
         'set_max_fanout 32 [current_design]']
    clks = []
    if E.ck:
        L.append(f'create_clock -name ck -period {T_PS} [get_ports {{ck[0]}}]')
        clks.append('ck')
    for p, i in sorted(set(E.clk_in)):
        n = f'f_{p}{i}'
        L.append(f'create_clock -name {n} -period {T_PS} [get_ports {{{p}[{i}]}}]')
        clks.append(n)
    for (p, i), src, inv in E.clk_out:
        n = f'o_{p}{i}'
        s = 'ck' if src[0] == 'ck' else f'f_{src[0]}{src[1]}'
        sp = '{ck[0]}' if src[0] == 'ck' else f'{{{src[0]}[{src[1]}]}}'
        L.append(f'create_generated_clock -name {n} -source [get_ports {sp}] -master_clock {s} -divide_by 1 '
                 f'{"-invert " if inv else ""}[get_ports {{{p}[{i}]}}]')
        clks.append(n)
    L.append('set_clock_uncertainty -setup 60 [all_clocks]')
    L.append('set_clock_uncertainty -hold 25 [all_clocks]')
    byclk = {}
    for (p, i), c in E.ins.items():
        byclk.setdefault('ck' if c[0] == 'ck' else f'f_{c[0]}{c[1]}', []).append(f'{p}[{i}]')
    for c, ps in sorted(byclk.items()):
        L.append(f'set_input_delay {IOD} -clock {c} [get_ports {{{" ".join(sorted(ps))}}}]')
    byo = {}
    for (p, i), o in E.outs.items():
        byo.setdefault('ck' if o[0] == 'ck' else f'o_{o[1][0]}{o[1][1]}', []).append(f'{p}[{i}]')
    for c, ps in sorted(byo.items()):
        fall = '' if c == 'ck' else '-clock_fall '
        L.append(f'set_output_delay {IOD} -clock {c} {fall}[get_ports {{{" ".join(sorted(ps))}}}]')
    L.append('set_load 2.0 [all_outputs]')
    if 'rst' in rec['ports']:
        for c in clks:
            if not c.startswith('o_'):
                L.append(f'set_input_delay {IOD} -clock {c} -add_delay [get_ports {{rst[0]}}]')
    # mesochronous crossings (forwarded clock <-> ck): the ot_meso_fifo contract
    if E.ck:
        for c in clks:
            if c.startswith('f_'):
                for a_, b_ in ((c, 'ck'), ('ck', c)):
                    L.append(f'set_max_delay -ignore_clock_latency -from [get_clocks {a_}] -to [get_clocks {b_}] 356.667')
                    L.append(f'set_min_delay -ignore_clock_latency -from [get_clocks {a_}] -to [get_clocks {b_}] 0')
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['emit'])
    ap.add_argument('--ports', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--master', action='append')
    ap.add_argument('--margin', action='store_true',
                    help='owner margin rule (2026-10-06): every face pin of a meso crossing registered -- the FIFO input '
                         'captured at the pin on the write clock (ot_hbm_stn_meso RI=1, +1 cycle), the FIFO readout '
                         'registered at its select (RDREG=1, +1 cycle), its receive buffer dropped (NOBP=1: stations never back-pressure), and every ck-domain output it feeds launched '
                         'from a register of its own per port (+1 cycle)')
    a = ap.parse_args(argv)
    fcm = fc_map()
    pdir = Path(a.ports)
    out = Path(a.out)
    names = a.master or sorted(p.name for p in pdir.iterdir() if p.is_dir() and
                               p.name.split('_')[1] in ('stn', 'meso', 'mcast', 'gath', 'cdist'))
    summary = {}
    for n in names:
        rec = json.loads((pdir / n / 'ports.json').read_text())
        E, role = build(rec, fcm, margin=a.margin)
        Em, _ = build(rec, fcm, mutant=True, margin=a.margin)
        d = out / n
        d.mkdir(parents=True, exist_ok=True)
        (d / f'{n}.sv').write_text(module_text(rec, E))
        (d / f'{n}_mutant.sv').write_text(module_text(rec, Em))
        (d / f'{n}.sdc').write_text(sdc_text(rec, E))
        (d / f'{n}_sim.sv').write_text(sim_text(rec, E, n + '_sim'))
        (d / f'{n}_mutant_sim.sv').write_text(sim_text(rec, Em, n + '_sim'))
        fcs = {p: E.fcm.get((n, p)) for p in rec['ports'] if p not in ('ck', 'rst')}
        (d / 'map.json').write_text(json.dumps(dict(master=n, role=role, forwarded=fcs, map=E.map,
                                                    clk_in=sorted({f'{p}[{i}]' for p, i in E.clk_in}),
                                                    clk_out={f'{p}[{i}]': (('ck' if s[0] == 'ck' else f'{s[0]}[{s[1]}]'), inv)
                                                             for (p, i), s, inv in E.clk_out},
                                                    ins={f'{p}[{i}]': ('ck' if c[0] == 'ck' else f'{c[0]}[{c[1]}]')
                                                         for (p, i), c in E.ins.items()}), indent=0) + '\n')
        summary[n] = dict(role=role, fwd=sum('ot_hbm_stn_fwd' in l for l in E.body),
                          meso=sum('ot_hbm_stn_meso' in l for l in E.body),
                          launch=sum('ot_hbm_stn_launch' in l for l in E.body), outputs_mapped=len(E.map))
    (out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    raise SystemExit(main())
