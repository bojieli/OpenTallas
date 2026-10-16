#!/usr/bin/env python3
"""qwen-split/kvsys v1.3 (2026-10-14, die lead r4): DIE-PLACED LEAVES.  A wires-only parent frame of the KV/system die
case (head, engine control, controller strip, ...) is replaced by its CLOSED leaves, each placed in the die at its
planned sub-slot and bound to its own closed view (exact LEF + TT/FF/SS ETM + insertion.json -> phi - R clock), so the
die STA times every leaf-to-leaf and leaf-to-die path on real views instead of the frame's ASSUMED single-flop ends.

Connectivity is bit-exact: yosys elaborates the parent RTL module (BINDINGS[frame]['module']) with every child as a
black box (ports from the child view's LEF: name, width, direction), and writes the parent's port and cell bit
connections.  Die port bits map to parent RTL port bits by the BINDINGS convention (die port dp -> concatenation of
BINDINGS ports, LSB first; 'sliced' die ports continue the base port after its bits, base first, others sorted), so a
child pin bit lands on (a) the die net bit of the frame's die port it was wired to, (b) a die wire private to the frame
instance (leaf-to-leaf), or (c) a strap: a constant (RTL literal) or a 'classed' strap port (head index, engine/stack
id) = a tie at that leaf's pin, carried on a net local to that one leaf.

    kv_expand.py --run RUN [--only qkd_rhead,qkd_ectl,...]
rewrites RUN/case_kv/{die.v, place.tcl, elements.lef} (originals kept as *.preexp), adds RUN/libs/qfd_etm_<leaf>_<c>.lib
and the leaves to RUN/libs/views.json (expanded_from), writes RUN/expand.json (per frame: leaves, nets, straps, checks).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_die as K  # noqa: E402
from binding_order import sliced_order

CORNERS = ('tt', 'ff', 'ss')
RT = 'physical/ref_tile'
# closed leaf views (module -> view dir); every leaf of an expanded frame must have one
VIEWS = dict(
    ot_qkh_head_frontq_native=f'{RT}/qkh_r4_frontq_1014/views/ot_qkh_head_frontq_native',
    ot_qkh_head_stin_native=f'{RT}/qkh_r3_stin_1014/views/ot_qkh_head_stin_native',
    ot_qkh_head_stk_native=f'{RT}/qkh_r3_stk_1014/views/ot_qkh_head_stk_native',
    ot_qkh_head_nb_native=f'{RT}/qkh_r3_nb_1014/views/ot_qkh_head_nb_native',
    ot_qkh_lane8=f'{RT}/ot_qkh_lane8_m5/views/ot_qkh_lane8',
    ot_qkh_ktree=f'{RT}/ot_qkh_ktree_m5/views/ot_qkh_ktree',
    ot_qkh_head_score4_native=f'{RT}/qkh_r4_score4_1014/views/ot_qkh_head_score4_native',
    qkd_ectl_a_tp8_direct=f'{RT}/qkd_ectl_a_tp8_direct/views/qkd_ectl_a_tp8_direct',
    qkd_ectl_a_tp8_epoch_direct=f'{RT}/qkd_ectl_a_tp8_direct/views/qkd_ectl_a_tp8_epoch_direct',
    qkd_ectl_b_tp8_direct=f'{RT}/qkd_ectl_b_tp8_direct/views/qkd_ectl_b_tp8_direct',
    qkd_ectl_c_tp8_direct=f'{RT}/qkd_ectl_c_tp8_direct/views/qkd_ectl_c_tp8_direct',
    qkd_ctrl_pc=f'{RT}/qkd_ctrl_pc/views/qkd_ctrl_pc',
    qkd_ctrl_kc=f'{RT}/qkd_ctrl_kc/views/qkd_ctrl_kc',
    # v1.4.3 near-head feed-through leaves (the far head's T1 / S2)
    qkh_head_gather_stage=f'{RT}/qkh_head_gather_stage/views/qkh_head_gather_stage',
    qkh_head_sstage=f'{RT}/qkh_head_sstage/views/qkh_head_sstage',
)
SR = 'rtl/qwen_sys/split_20261014'
RTL = dict(ot_qkh_head_frontq_native=f'{SR}/ot_qkh_head_native_r4.sv', ot_qkh_head_score4_native=f'{SR}/ot_qkh_head_native_r4.sv',
           ot_qkh_head_stin_native=f'{SR}/ot_qkh_head_native.sv', ot_qkh_head_stk_native=f'{SR}/ot_qkh_head_native_r3.sv',
           ot_qkh_head_nb_native=f'{SR}/ot_qkh_head_native_r3.sv', ot_qkh_lane8='rtl/hdc/nearhbm/ot_qkh_subtiles.sv',
           ot_qkh_ktree='rtl/hdc/nearhbm/ot_qkh_subtiles.sv',
           **{f'qkd_ectl_{x}_tp8_direct': f'{SR}/qkd_ectl_native_direct_tp8.sv' for x in 'abc'},
           qkd_ectl_a_tp8_epoch_direct=f'{SR}/qkd_ectl_a_tp8_epoch_direct.sv',
           qkd_ctrl_pc='rtl/qwen_sys/kv_die_20261009/qkd_ctrl_strip.sv', qkd_ctrl_kc='rtl/qwen_sys/kv_die_20261009/qkd_ctrl_strip.sv',
           qkh_head_gather_stage=f'{SR}/qkh_head_gather_stage.sv', qkh_head_sstage=f'{SR}/qkh_head_stages.sv')
FLIP = dict(R0=(0, 0), MX=(0, 1), MY=(1, 0), R180=(1, 1))
ORIENT = {v: k for k, v in FLIP.items()}


# ---- per-frame placement plans: yosys cell name -> (x, y, orient) in the frame's canonical (R0) coordinates -------------
def _head_plan(ft=False):
    pl = json.loads((ROOT / (K.HEAD_FT_PLAN if ft else 'results/arch/qwen_split_1014/head_native_r4_codex_1014/plan.json')).read_text())['children']
    if ft:      # v1.4.3: the far neighbour's T1 / S2 in the feed-through channel
        pl = dict(pl, ftg=[*K.V143_FT['ftg'], *K.HGS], fts=[*K.V143_FT['fts'], *K.HSS])

    def name(cell):
        m = re.fullmatch(r'g_front\[(\d+)\]\.u_front', cell)
        if m:
            return f'front{m.group(1)}'
        m = re.fullmatch(r'g_t\[(\d+)\]\.u_(stin|stk|nb1|nb2|l8)', cell)
        if m:
            t, k = m.groups()
            return dict(stin=f'stin{t}', stk=f'stk{t}', nb1=f'nb1_{t}', nb2=f'nb2_{t}', l8=f'lane{t}')[k]
        return dict(u_kt='ktree', u_score='score', u_ftg='ftg', u_fts='fts')[cell]
    return lambda cell, fw, fh: (pl[name(cell)][0], pl[name(cell)][1], 'R0')


def _ectl_plan():
    x = dict(u_a=0.0, u_b=254.88, u_c=509.76)       # contract v1.1 sub-slots A | B | C x 129.6 (pins/qkd_ectl.json)
    return lambda cell, fw, fh: (x[cell], 0.0, 'R0')


def _ctrl_plan(rev):
    # PC k: its PHY-face po word level with the PHY abstract's po<k> (strip y 378 k + 200 = PHY y 378 k + 128.7 + 71.28);
    # view po centre y 38.0 (R0) / 134.8 (MX).  kc leaf at the strip's OUTER end, under the frame's kc pin (x = w / 2).
    def f(cell, fw, fh):
        if cell == 'u_kc':
            return (round(fw / 2 - 23.76, 3), 0.0 if rev else round(fh - 43.2, 3), 'MX' if rev else 'R0')
        k = int(cell[4:])
        return (0.0, round(378.0 * k + (65.2 if rev else 162.0), 3), 'MX' if rev else 'R0')
    return f


def frames():
    return dict(
        qkd_rhead=dict(plan=_head_plan(), straps=lambda inst: dict(hid=int(inst.rsplit('_', 1)[1]))),
        qkd_rhead_ft=dict(plan=_head_plan(True), straps=lambda inst: dict(hid=int(inst.rsplit('_', 1)[1]))),
        qkd_ectl=dict(plan=_ectl_plan(),
                      straps=lambda inst: dict(cfg=(int(inst.split('_')[2]) << 2) | K.STACKS.index(inst.split('_')[1]))),
        qkd_ctrl=dict(plan=_ctrl_plan(True), straps=lambda inst: {}),
        qkd_ctrl_n=dict(plan=_ctrl_plan(False), straps=lambda inst: {}),
    )


# ---- LEF / RTL helpers --------------------------------------------------------------------------------------------------
def lef_macro(path):
    t = Path(path).read_text()
    m = re.search(r'^MACRO (\S+)\s*$', t, re.M)
    e = re.search(rf'^END {re.escape(m.group(1))}\s*$', t[m.end():], re.M)
    blk = t[m.start():m.end() + e.end()]
    sz = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', blk)
    ports = {}
    for pm in re.finditer(r'^  PIN (\S+)\s*$(.*?)^  END \1\s*$', blk, re.M | re.S):
        n = pm.group(1)
        if n in ('VDD', 'VSS'):
            continue
        d = re.search(r'DIRECTION\s+(\w+)', pm.group(2))
        bm = re.fullmatch(r'(.+)\[(\d+)\]', n)
        base, i = (bm.group(1), int(bm.group(2))) if bm else (n, None)
        r = ports.setdefault(base, dict(dir=(d.group(1).lower() if d else 'input'), bits=set()))
        r['bits'].add(i)
    return m.group(1), blk, (float(sz.group(1)), float(sz.group(2))), ports


def stub_text(mod, ports, params):
    L = [f'(* blackbox *) module {mod} #(' + ', '.join(f'parameter {p} = 0' for p in sorted(params)) + ') ('
         if params else f'(* blackbox *) module {mod} (']
    items = []
    for p, r in sorted(ports.items()):
        d = {'input': 'input', 'output': 'output', 'inout': 'inout'}.get(r['dir'], 'input')
        idx = [i for i in r['bits'] if i is not None]
        rng = f'[{max(idx)}:0] ' if idx else ''
        items.append(f'  {d} wire {rng}{p}')
    return '\n'.join(L) + '\n' + ',\n'.join(items) + '\n);\nendmodule\n'


def module_text(path, mod):
    t = Path(path).read_text()
    m = re.search(rf'^\s*module\s+{re.escape(mod)}\b', t, re.M)
    e = re.search(r'^\s*endmodule\b', t[m.end():], re.M)
    pre = '`timescale 1ns/1ps\n'
    body = t[m.start():m.end() + e.end()]
    # yosys 0.9 has no SV size casts: N'(expr) on a port connection -> (expr) (the port width truncates it the same way)
    body = re.sub(r"\b\d+'\(", '(', body)
    return pre + body + '\n'


def elaborate(mod, file, leaf):
    """yosys JSON of the parent module with every leaf module a black box."""
    txt = module_text(ROOT / file, mod)
    params = defaultdict(set)
    for cm in re.finditer(r'\b(\w+)\s*#\s*\((.*?)\)\s*(\w+)\s*\(', txt, re.S):
        if cm.group(1) in leaf:
            params[cm.group(1)] |= set(re.findall(r'\.(\w+)\s*\(', cm.group(2)))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / 'stubs.v').write_text('\n'.join(stub_text(m_, leaf[m_]['ports'], params[m_]) for m_ in leaf))
        (td / 'parent.sv').write_text(txt)
        (td / 'run.ys').write_text(f'read_verilog -sv {td}/stubs.v\nread_verilog -sv {td}/parent.sv\n'
                                   f'hierarchy -top {mod}\nproc\nopt_clean\nwrite_json {td}/out.json\n')
        r = subprocess.run(['yosys', '-q', '-s', str(td / 'run.ys')], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f'yosys {mod}: {r.stderr[-2000:]}')
        return json.loads((td / 'out.json').read_text())['modules'][mod]


def base_type(t):
    return t.split('\\')[1] if t.startswith('$paramod') else t.lstrip('\\')


# ---- die.v -------------------------------------------------------------------------------------------------------------
def parse_conns(body):
    return [(c.group(1).lstrip('\\').strip(), c.group(2).strip()) for c in
            re.finditer(r'\.(\\?\S+?)\((\{[^}]*\}|[^)]*)\)', body)]


def net_bits(expr, wires):
    """die net expression -> list of bit refs, LSB first"""
    parts = [x.strip() for x in expr.strip('{}').split(',') if x.strip()] if expr.startswith('{') else [expr]
    out = []
    for p in reversed(parts):           # concatenation lists MSB part first
        b = re.fullmatch(r'(\S+)\[(\d+)(?::(\d+))?\]', p)
        if b:
            hi = int(b.group(2))
            lo = int(b.group(3)) if b.group(3) else hi
            out += [f'{b.group(1)}[{i}]' for i in range(lo, hi + 1)]
        else:
            out += [f'{p}[{i}]' for i in range(wires.get(p, 1))]
    return out


def pack(bits):
    """bit refs (LSB first) -> a compact Verilog concatenation (MSB first), runs of one wire as slices"""
    runs = []
    for b in bits:
        m = re.fullmatch(r'(\S+)\[(\d+)\]', b)
        if m and runs and runs[-1][0] == m.group(1) and runs[-1][2] == int(m.group(2)) - 1:
            runs[-1][2] += 1
        elif m:
            runs.append([m.group(1), int(m.group(2)), int(m.group(2))])
        else:
            runs.append([b, None, None])
    parts = []
    for n, lo, hi in reversed(runs):
        parts.append(n if lo is None else (f'{n}[{lo}]' if lo == hi else f'{n}[{hi}:{lo}]'))
    return parts[0] if len(parts) == 1 else '{' + ', '.join(parts) + '}'


def die_to_rtl(master, die_ports, rtl_w):
    """die port -> RTL port bit names (LSB first) per BINDINGS, exactly the bind_views / kv_relays convention"""
    b = K.BINDINGS[master]
    sl = b.get('sliced', {})
    groups = defaultdict(list)
    for dp in die_ports:
        base = dp if dp in b['ports'] else sl.get(dp)
        if base is None:
            raise ValueError(f'{master}: die port {dp} has no binding')
        groups[base].append(dp)
    out = {}
    for base, dps in groups.items():
        seq = []
        for rp in b['ports'][base]:
            seq += [(rp, i) for i in range(rtl_w[rp])]
        order = sliced_order(base, dps)
        k = 0
        for d in order:
            n = die_ports[d]
            out[d] = seq[k:k + n]
            k += n
        if k != len(seq):
            raise ValueError(f'{master}: die ports {order} carry {k} bits, RTL {b["ports"][base]} {len(seq)}')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--only', default='')
    a = ap.parse_args(argv)
    K._set_geometry(True)
    case, libs = a.run / 'case_kv', a.run / 'libs'
    FR = frames()
    only = [x for x in a.only.split(',') if x] or list(FR)
    dv = (case / 'die.v').read_text()
    lines = dv.split('\n')
    wires = {}
    for ln in lines:
        m = re.match(r'\s*wire\s+\[(\d+):0\]\s+(\S+);', ln)
        if m:
            wires[m.group(2)] = int(m.group(1)) + 1
        else:
            m = re.match(r'\s*wire\s+(\S+);', ln)
            if m:
                wires[m.group(1)] = 1
    place = (case / 'place.tcl').read_text().split('\n')
    plc = {}
    for i, ln in enumerate(place):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', ln)
        if m:
            plc[m.group(1)] = (i, float(m.group(2)), float(m.group(3)), m.group(4))
    elef = (case / 'elements.lef').read_text()
    fsize = {}
    for m in re.finditer(r'^MACRO (\S+)\s*$.*?\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', elef, re.M | re.S):
        fsize[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    leaf = {}
    for mod, vd in VIEWS.items():
        lef = ROOT / vd / f'{mod}.lef'
        if lef.exists():
            nm, blk, sz, ports = lef_macro(lef)
            for r in ports.values():
                r['w'] = 1 if r['bits'] == {None} else max(r['bits']) + 1
            leaf[nm] = dict(view=vd, lef=blk, size=sz, ports=ports)
    views = json.loads((libs / 'views.json').read_text())
    rep = dict(schema='opentallas.qwen_kvsys_expand.v1', frames={})
    new_lines, add_wires, add_place, drop_inst, used_leaf = [], [], [], set(), set()
    inst_re = re.compile(r'^\s+(\w+) (\S+) \((.*)\);\s*$')
    jcache = {}
    for ln in lines:
        m = inst_re.match(ln)
        if not m or m.group(1) not in only or m.group(1) not in FR:
            new_lines.append(ln)
            continue
        mst, inst, body = m.groups()
        spec = FR[mst]
        b = K.BINDINGS[mst]
        if mst not in jcache:
            jcache[mst] = elaborate(b['module'], b['file'], leaf)
        J = jcache[mst]
        rtl_w = {p: len(v['bits']) for p, v in J['ports'].items()}
        conns = parse_conns(body)
        dpw = {p: len(net_bits(e, wires)) for p, e in conns}
        mp = die_to_rtl(mst, dpw, rtl_w)
        bitnet = {}                                       # yosys bit id -> die bit ref
        for p, e in conns:
            for (rp, i), nb_ in zip(mp[p], net_bits(e, wires)):
                bid = J['ports'][rp]['bits'][i]
                if isinstance(bid, str):
                    continue                              # parent port bit tied inside the parent: nothing to connect
                if bid in bitnet and bitnet[bid] != nb_:
                    raise ValueError(f'{inst}: parent bit {rp}[{i}] on two die nets {bitnet[bid]} / {nb_}')
                bitnet[bid] = nb_
        straps = spec['straps'](inst)
        strap_bits = {}
        for sp, val in straps.items():
            for i, bid in enumerate(J['ports'][sp]['bits']):
                if not isinstance(bid, str):
                    strap_bits[bid] = '1' if (val >> i) & 1 else '0'
        unbound_ports = sorted(p for p in J['ports'] if p not in {rp for v in mp.values() for rp, _ in v} and p not in straps)
        unbound_inputs = [p for p in unbound_ports if J['ports'][p]['direction'] == 'input']
        if unbound_inputs:
            raise ValueError(f'{inst}: functional parent inputs without die bindings {unbound_inputs}')
        # internal (leaf-to-leaf) wire names from the parent's netnames
        names = {}
        for nn, nv in sorted(J['netnames'].items(), key=lambda kv: (kv[1].get('hide_name', 0), len(kv[0]))):
            for i, bid in enumerate(nv['bits']):
                if not isinstance(bid, str) and bid not in names:
                    names[bid] = (nn, i, len(nv['bits']))
        iw = {}
        tie_values = {}

        def ref(bid, cell):
            if isinstance(bid, str) or bid in strap_bits:
                v = bid if isinstance(bid, str) else strap_bits[bid]
                if v not in ('0', '1'):
                    raise ValueError(f'{inst}/{cell}: undefined constant {v}')
                tn = f'n_{inst}__{re.sub(r"[^A-Za-z0-9_]", "_", cell)}__tie{v}'
                iw[tn] = 1
                tie_values[tn] = v
                return f'{tn}[0]'
            if bid in bitnet:
                return bitnet[bid]
            nn, i, w = names[bid]
            wn = f'n_{inst}__{re.sub(r"[^A-Za-z0-9_]", "_", nn.lstrip(chr(92)))}'
            iw[wn] = max(iw.get(wn, 0), w)
            return f'{wn}[{i}]'
        fx, fy, fo = plc[inst][1], plc[inst][2], plc[inst][3]
        fw, fh = fsize[mst]
        ff = FLIP[fo]
        nleaf, conn_bits, tie_bits = 0, 0, 0
        drivers = defaultdict(int)
        inputs = set()
        rectangles = []
        for cname, c in J['cells'].items():
            cell = cname.lstrip('\\')
            ct = base_type(c['type'])
            if ct not in leaf:
                raise ValueError(f'{mst}: child {cell} ({ct}) has no closed view (glue is not expanded)')
            used_leaf.add(ct)
            L = leaf[ct]
            cx, cy, co = spec['plan'](cell, fw, fh)
            w_, h_ = L['size']
            # Generated frame outlines shave 24 nm from the nominal contract.
            # Match bind_views' 50 nm outline tolerance while rejecting real spill.
            if min(cx, cy) < -0.001 or cx + w_ > fw + 0.05 or cy + h_ > fh + 0.05:
                raise ValueError(f'{inst}/{cell}: closed leaf outside contract frame')
            rect = (cell, cx, cy, cx + w_, cy + h_)
            for other in rectangles:
                if min(rect[3], other[3]) - max(rect[1], other[1]) > 0.001 and \
                   min(rect[4], other[4]) - max(rect[2], other[2]) > 0.001:
                    raise ValueError(f'{inst}: overlapping closed leaves {cell} / {other[0]}')
            rectangles.append(rect)
            px = fw - cx - w_ if ff[0] else cx
            py = fh - cy - h_ if ff[1] else cy
            cf = FLIP[co]
            orient = ORIENT[(ff[0] ^ cf[0], ff[1] ^ cf[1])]
            cinst = f'{inst}__{re.sub(r"[^A-Za-z0-9_]", "_", cell)}'
            pc = []
            for p, bits in c['connections'].items():
                if p not in L['ports']:
                    raise ValueError(f'{cinst}: RTL port {p} not a pin of view {ct}')
                if L['ports'][p]['w'] != len(bits):
                    raise ValueError(f'{cinst}: port {p} RTL {len(bits)} b vs view {L["ports"][p]["w"]} b')
                refs = [ref(bid, cell) for bid in bits]
                conn_bits += len(bits)
                tie_bits += sum('__tie' in r_ for r_ in refs)
                if L['ports'][p]['dir'] == 'input':
                    inputs.update(bid for bid in bits if not isinstance(bid, str))
                if L['ports'][p]['dir'] == 'output':
                    for bid in bits:
                        if not isinstance(bid, str):
                            drivers[bid] += 1
                pc.append(f'.{p}({pack(refs)})')
            miss = sorted(set(L['ports']) - set(c['connections']))
            if miss:
                raise ValueError(f'{cinst}: view pins without an RTL connection {miss[:6]}')
            new_lines.append(f'  {ct} {cinst} ({", ".join(pc)});')
            add_place.append(f'ot_mts::place [$_blk findInst {cinst}] {fx + px:.3f} {fy + py:.3f} {orient}')
            nleaf += 1
        multi = [bid for bid, n in drivers.items() if n > 1]
        if multi:
            raise ValueError(f'{inst}: {len(multi)} bits with several leaf drivers')
        available = set(drivers) | set(strap_bits) | {bid for p in J['ports'].values()
                    if p['direction'] == 'input' for bid in p['bits'] if not isinstance(bid, str)}
        undriven = sorted(inputs - available)
        if undriven:
            raise ValueError(f'{inst}: {len(undriven)} undriven child-input bits {undriven[:8]}')
        for wn, w in iw.items():
            add_wires.append(f'  wire [{w - 1}:0] {wn};')
            if wn in tie_values:
                add_wires.append(f"  assign {wn} = 1'b{tie_values[wn]};")
        drop_inst.add(inst)
        fr = rep['frames'].setdefault(mst, dict(module=b['module'], instances=0, leaves_per_instance=nleaf,
                                                 internal_wires_per_instance=len(iw), straps=sorted(straps),
                                                 rtl_ports_without_die_port=unbound_ports, leaf_pin_bits=conn_bits,
                                                 tie_pin_bits=tie_bits, connectivity_checks=dict(undriven_inputs=0, multiple_drivers=0,
                                                 unbound_parent_inputs=0, overlaps=0, outside_slot=0)))
        fr['instances'] += 1
    if not drop_inst:
        print('nothing expanded')
        return 1
    # die.v: wires after the module header's existing wires
    k = max(i for i, ln in enumerate(new_lines) if re.match(r'\s*wire\b', ln))
    new_lines[k + 1:k + 1] = add_wires
    for f in ('die.v', 'place.tcl', 'elements.lef'):
        if not (case / f'{f}.preexp').exists():
            shutil.copy(case / f, case / f'{f}.preexp')
    (case / 'die.v').write_text('\n'.join(new_lines))
    keep = [ln for i, ln in enumerate(place) if not any(i == plc[x][0] for x in drop_inst)]
    j = max(i for i, ln in enumerate(keep) if 'ot_mts::place' in ln)
    keep[j + 1:j + 1] = add_place
    (case / 'place.tcl').write_text('\n'.join(keep))
    # LEF: add each leaf view MACRO once (exact text)
    add_lef = [leaf[m_]['lef'] for m_ in sorted(used_leaf) if not re.search(rf'^MACRO {m_}\s*$', elef, re.M)]
    t = elef.rstrip()
    end = re.search(r'^END LIBRARY\s*$', t, re.M)
    t = (t[:end.start()] + '\n'.join(add_lef) + '\n' + t[end.start():]) if end else t + '\n' + '\n'.join(add_lef) + '\n'
    (case / 'elements.lef').write_text(t + '\n')
    # libs + views
    for m_ in sorted(used_leaf):
        vd = ROOT / leaf[m_]['view']
        for c in CORNERS:
            src = vd / f'{m_}_{c}.lib'
            if not src.exists():
                if c == 'ss':
                    continue
                raise FileNotFoundError(src)
            txt = src.read_text()
            txt = re.sub(r'library\s*\(\s*"?[^")]+"?\s*\)', f'library (qfd_etm_{m_}_{c})', txt, count=1)
            (libs / f'qfd_etm_{m_}_{c}.lib').write_text(txt)
        views['views'][m_] = dict(bound=True, view=leaf[m_]['view'], module=m_, real_um=list(leaf[m_]['size']),
                                  expanded_from=sorted({f for f, r in rep['frames'].items()}), cls='die_placed_leaf')
    views.setdefault('expanded', {}).update({f: r['module'] for f, r in rep['frames'].items()})
    (libs / 'views.json').write_text(json.dumps(views, indent=1) + '\n')
    rep['leaves'] = {m_: dict(view=leaf[m_]['view'], rtl=RTL[m_]) for m_ in sorted(used_leaf)}
    rep['instances_removed'] = len(drop_inst)
    rep['instances_added'] = len(add_place)
    (a.run / 'expand.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(dict(removed=len(drop_inst), added=len(add_place), wires=len(add_wires),
                          frames={k_: (v['instances'], v['leaves_per_instance'], v['tie_pin_bits']) for k_, v in rep['frames'].items()})))
    return 0


if __name__ == '__main__':
    sys.exit(main())
