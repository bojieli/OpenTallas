#!/usr/bin/env python3
"""Q-KVSYS-RLY 2026-10-16 (owner rule 19:50 PT 10-15 'fewer distinct tiles'; VIS-ROM QKV-04): KV/system die RELAY STANDARDS.

The KV die generator emits one relay master per bus width, qkd_rly_<W> (21 masters, 8,276 instances in kvs11-v143c), each
an unrouted frame whose pins sit on M4 at minimum pitch (20.9 pins/um).  With OT_KV_RLY_STD=1 every relay stage binds to
replicas of FOUR hardened standards (rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv, kits physical/ref_tile/qkd_rlys_<S>):

    qkd_rlys_1    12.96 x 12.96 um    1 b   (reset / boot tree hops qkd_rly_t1, 1-bit words, reverse bits)
    qkd_rlys_36   12.96 x 12.96 um   36 b
    qkd_rlys_296  21.6  x 47.52 um  296 b
    qkd_rlys_528  21.6  x 82.08 um  528 b   (face <= 86.4 um = a 129.6-um relay channel minus 2 x 21.6-um block keep-outs)

all W/E pins on M4 at 3 tracks (<= 6.94 pins/um, rule <= 8 pins/um/layer), one flop a bit, no reset, 1 cycle a stage (the
die plan's relay_stages are unchanged).  A stage of W bits (F forward, R reverse) = replicas(F) + R x qkd_rlys_1 placed as a
ROW inside the relay frame: replicas left to right, REPLICA_GAP apart (the gap is the M4 <-> M6 via-access corridor of the
next replica's W face and the previous one's E face), vertically centred.  Spare input bits of a replica are tied low as
DECLARED pads (die.v.pads.json, tools/die_port_bind.py PADS); spare output bits drive private open wires.

    replicas(W), layout(W, rev) -- shared by kv_die.py (frame size, OT_KV_RLY_STD=1) and the netlist pass below
    kv_rly_std.py --run RUN [--dry-run]
        rewrites RUN/case_kv/{die.v, place.tcl, elements.lef} (originals kept as *.prestd), adds the standards' closed views
        to RUN/libs (qfd_etm_<std>_<c>.lib, views.json) and to RUN/expand.json 'leaves' (die_port_bind_kv --expanded),
        writes RUN/case_kv/die.v.pads.json and RUN/rly_std.json.  The per-bit direction is RUN/relays.json (kv_relays.py).
"""
import argparse
import itertools
import json
import math
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RT = 'physical/ref_tile'
RTL = 'rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv'
STD = {1: (12.96, 12.96), 36: (12.96, 12.96), 296: (21.6, 47.52), 528: (21.6, 82.08)}
# KV-LANDSLOT 10-18: the LANDING outlines of the forwarded-lane kits (tools/qwen_kv_die/gen_kv_fwd_lane.py LAND on
# claude/kv-lanekits-1018: qkd_landsh{,0}_<S>; the 36 / 296 / 528 landings gate at 181 / 128 / 126 % in the station
# outline).  A relay frame the die planner reserved as a landing (master qkd_rly_<W>_land, kv_land_slot.py) lays its
# forward replicas out at these outlines, so kv_fwd_lanes.py can bind qkd_landsh*_<S> in place
LAND = {1: (12.96, 12.96), 36: (25.92, 21.6), 296: (51.84, 47.52), 528: (51.84, 82.08)}
LAND_SUFFIX = '_land'
REPLICA_GAP = 10.8
GY = 2.16
CORNERS = ('tt', 'ff', 'ss')
FLIP = dict(R0=(0, 0), MX=(0, 1), MY=(1, 0), R180=(1, 1))
ORIENT = {v: k for k, v in FLIP.items()}
# buses whose die direction model carries reverse bits (kvs11-v143c relays.json: kvn 1048 / hb 284 / emf 289 / emr 521, one
# bit each): their frames reserve one qkd_rlys_1 slot; the netlist pass refuses a relay with more reverse bits than reserved
# reverse bits per relayed bus (the die direction model, tools/die_top_lint.py endpoint_dirs, as relays.json measures it):
# kvs11-v143c kvn 1048 / hb 284 / emf 289 / emr 521 carry one reverse bit each; Q-KVSYS-NETLIST 7ffb0ff53 made host_fdi
# (2089 b) per-bit: 1,044 host -> SerDes forward, 1,045 (tx_up, rx_v, rx_flit) SerDes -> host reverse.  The frame reserves
# these; the netlist pass refuses a relay whose measured reverse count differs (fail closed)
REV_BITS = (('host_fdi', 1045), ('kvn', 1), ('hb', 1), ('emf', 1), ('emr', 1))
REV_BUS = re.compile(r'^(' + '|'.join(b for b, _ in REV_BITS) + r')(?:_|$)')
# replica choice: minimum (outline area + PAD_COST per tied bit + INST_COST per instance), at most 5 replicas
PAD_COST, INST_COST = 1.0, 60.0
# SQC-KDIE5 10-22 (OT_KV_GRP_PC_HCK=1; default off: die.v byte-identical): the group <-> PC words (slg o_pc<j> ->
# kvpc i_grp, kvpc o_grp -> slg i_pc<j>) are MIXED-domain in RTL (qkd_kvs_grp / _h, qkd_kvs_pc / _h: o_pc<j> = 95 hck
# bits -- boot CDC sink_*, front blk_go, phase *_h -- + 33 ck bits -- landing-cal r_*; i_grp consumes them on hck
# (cal_hck / front_hck) and ck (return path expected_*); o_grp = 295 ck + 10 hck status levels, consumed by the group's
# drain guard through its async_reg 2-flop synchronisers).  One relay stage on the core trunk put a core flop between
# two hck flops (1,280 unlanded crossings on kvs14r sqc3s).  With the knob every relay stage of such a chain is split
# by LAUNCH domain: the ck bits keep their replicas on the stage's core trunk, the hck bits ride their own replicas on
# the chain source frame's HBM clock (its 'hck' net, n_clk_hbm_<stack>) -- the kv_die.py DOMSPLIT convention (relay
# clock = launching pin's domain; a crossing stays at the consumer's synchroniser), without the DOMSPLIT RTL re-cut.
# Per-bit domains: the producer field layout of the generated tiles (kv_static_die.all_tiles) x the measured field
# domains (kv_static_die.DOMSPLIT_TABLE), fail closed on a field without one; cross-checked bit-exact against the
# RTL-elaborated frame pin roots (kv_frame_pin_roots.py, kvs14r sqc3s: 0 mismatches).  The split row must fit the
# planned frame (fail closed).  The group gather o_ctl stays as is (its hck levels need the DOMSPLIT in-group landing).
GRP_PC_HCK = os.environ.get('OT_KV_GRP_PC_HCK', '0') == '1'
GRP_PC_PORTS = re.compile(r'^(o_pc\d|o_grp)$')
GRP_PC_INST = re.compile(r'^(slg|kvpc)_(WS|WN|ES|EN)_\d+$')


def name(s):
    return f'qkd_rlys_{s}'


def replica_pads(s, used):
    """One replica's exact paired tie-low inputs / unused registered outputs; never a master-wide minimum."""
    if s not in STD or type(used) is not int or not 0 < used <= s:
        raise ValueError(f'invalid standard replica padding {used}/{s}')
    if used == s:
        return None
    return dict(master=name(s),
                reason='kv_rly_std replica: exactly these high a bits are tied zero and the matching b bits '
                       'drive private spare wires; lower logical bits remain required',
                ports={p: [[used, s - 1]] for p in ('a', 'b')})


def replicas(w):
    """standard widths for a w-bit forward word, widest first (deterministic)"""
    if w <= 0:
        return []
    if 0.7 * 528 <= w <= 528:
        # KVPLAN2 2215: a word that fills >= 70 % of one qkd_rlys_528 takes that one replica (21.6 um wide) instead of a
        # 296 + 3 x 36 row (93 um wide): a W-in / E-out stage on a vertical run gives up its frame width every hop (the
        # 384-b PV trunk segments; no other KV die word is 370..527 b today)
        return [528]
    best = None
    for k in range(1, 6):
        for combo in itertools.combinations_with_replacement(sorted(STD, reverse=True), k):
            if sum(combo) < w or sum(combo) - min(combo) >= w:
                continue
            cost = sum(STD[c][0] * STD[c][1] for c in combo) + PAD_COST * (sum(combo) - w) + INST_COST * k
            if best is None or cost < best[0] - 1e-9:
                best = (cost, list(combo))
    if best is None:
        raise ValueError(f'kv relay standards: {w} b needs more than 5 replicas')
    return best[1]


def dims(s, role='fwd', land=False):
    """outline of one replica slot: a landing frame's forward slots take the landing kit outline"""
    return LAND[s] if (land and role == 'fwd') else STD[s]


def layout(w, rev=0, land=False, split=None):
    """(frame w, frame h, [(std, dx, dy, role)]) of a w-bit relay stage with rev reverse bits (land: the forward
    replicas are landing slots, LAND outlines; the replica choice is unchanged).  split (OT_KV_GRP_PC_HCK): the forward
    bits' (ck, hck) counts -- each domain takes its own replicas, ck first"""
    # reverse bits ride their own replicas, MIRRORED (MY: a on the E face, b on the W face)
    fwd = replicas(w - rev) if split is None else replicas(split[0]) + replicas(split[1])
    reps = [(s, 'fwd') for s in fwd] + [(s, 'rev') for s in replicas(rev)]
    fh = max(dims(s, r, land)[1] for s, r in reps)
    out, x = [], 0.0
    for s, role in reps:
        sw, sh = dims(s, role, land)
        dy = round(math.floor((fh - sh) / 2 / GY + 1e-9) * GY, 4)
        out.append((s, round(x, 4), dy, role))
        x += sw + REPLICA_GAP
    return round(x - REPLICA_GAP, 4), fh, out


def frame_rev(bid):
    m = REV_BUS.match(bid)
    return dict(REV_BITS)[m.group(1)] if m else 0


# ---- die.v helpers (the kv_expand.py conventions) ---------------------------------------------------------------------
def net_bits(expr, wires):
    expr = expr.strip()
    b = re.fullmatch(r'(\S+)\[(\d+)(?::(\d+))?\]', expr)
    if b:
        hi = int(b.group(2))
        lo = int(b.group(3)) if b.group(3) else hi
        return [f'{b.group(1)}[{i}]' for i in range(lo, hi + 1)]
    if expr.startswith('{') or "'" in expr:
        raise ValueError(f'relay connection {expr!r}: expected a plain die net')
    return [f'{expr}[{i}]' for i in range(wires.get(expr, 1))]


def pack(bits):
    """bit refs (LSB first; '0' = a tie-low pad bit) -> Verilog concatenation, MSB first"""
    runs = []
    for b in bits:
        m = re.fullmatch(r'(\S+)\[(\d+)\]', b)
        if b == '0':
            if runs and runs[-1][0] == "'0":
                runs[-1][1] += 1
            else:
                runs.append(["'0", 1, None])
        elif m and runs and runs[-1][0] == m.group(1) and runs[-1][2] == int(m.group(2)) - 1:
            runs[-1][2] += 1
        elif m:
            runs.append([m.group(1), int(m.group(2)), int(m.group(2))])
        else:
            raise ValueError(b)
    parts = []
    for n, lo, hi in reversed(runs):
        parts.append(f"{lo}'b0" if n == "'0" else (f'{n}[{lo}]' if lo == hi else f'{n}[{hi}:{lo}]'))
    return parts[0] if len(parts) == 1 else '{' + ', '.join(parts) + '}'


def grp_pc_hck_domains(lines, wires):
    """OT_KV_GRP_PC_HCK: {relay inst: (frozenset of its HCK-launched bit indices, the source frame's hck net)} for every
    qkd_rly_* stage of a group <-> PC chain (traced back through relays to slg o_pc<j> / kvpc o_grp)"""
    sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
    import kv_static_die as KSD
    tiles = KSD.all_tiles()
    gen = re.compile(r'^\s+(\S+) (\S+) \((.*)\);\s*$')
    drv, relays, hck = {}, {}, {}
    for ln in lines:
        m = gen.match(ln)
        if not m or m.group(1) in ('wire', 'module', 'input', 'output', 'inout'):
            continue
        mst, inst, body = m.groups()
        conns = dict((c.group(1), c.group(2).strip()) for c in re.finditer(r'\.(\w+)\(([^()]*)\)', body))
        if mst.startswith('qkd_rly_'):
            relays[inst] = conns
            continue
        if not (GRP_PC_INST.match(inst) and mst.startswith('qkd_kvs_')):
            continue
        t = tiles.get(inst)
        if t is None or KSD._ds_bkind(t['kind']) not in ('grp', 'pc'):
            raise ValueError(f'OT_KV_GRP_PC_HCK: frame {inst} ({mst}) is not a generated group / PC tile')
        hck[inst] = conns.get('hck')
        for port, expr in conns.items():
            if not GRP_PC_PORTS.match(port):
                continue
            lay = t['ports'][port].get('layout')
            if not lay:
                raise ValueError(f'OT_KV_GRP_PC_HCK: {inst}.{port} has no field layout')
            dom = []
            for _pn, w_, key in lay:
                dom += [KSD.ds_domain(key)] * w_
            nb = net_bits(expr, wires)
            if len(nb) != len(dom):
                raise ValueError(f'OT_KV_GRP_PC_HCK: {inst}.{port} {len(nb)} b connected vs {len(dom)} b laid out')
            for b, d in zip(nb, dom):
                drv[b] = (inst, d)
    rdrv = {}
    for inst, cs in relays.items():
        for i, b in enumerate(net_bits(cs['b'], wires)):
            rdrv[b] = (inst, i)
    abits = {inst: net_bits(cs['a'], wires) for inst, cs in relays.items()}

    def source(b, seen=()):
        while b not in drv:
            if b not in rdrv:
                return None
            r, i = rdrv[b]
            if r in seen:
                raise ValueError(f'OT_KV_GRP_PC_HCK: relay loop at {r}')
            seen += (r,)
            b = abits[r][i]
        return drv[b]
    out = {}
    for inst in relays:
        src = [source(b) for b in abits[inst]]
        frames = {s[0] for s in src if s}
        if not frames:
            continue
        if len(frames) != 1 or any(s is None for s in src):
            raise ValueError(f'OT_KV_GRP_PC_HCK: relay {inst} mixes group / PC sources {sorted(frames)} with other bits')
        f = frames.pop()
        hb = frozenset(i for i, s in enumerate(src) if s[1] == 'hck')
        if hb:
            if not (hck.get(f) or '').startswith('n_clk_hbm_'):
                raise ValueError(f'OT_KV_GRP_PC_HCK: {inst} carries hck bits of {f} without an n_clk_hbm_* hck ({hck.get(f)})')
            out[inst] = (hb, hck[f])
    return out


def lef_macro(path):
    t = Path(path).read_text()
    m = re.search(r'^MACRO (\S+)\s*$', t, re.M)
    e = re.search(rf'^END {re.escape(m.group(1))}\s*$', t[m.end():], re.M)
    blk = t[m.start():m.end() + e.end()]
    sz = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', blk)
    return blk, (float(sz.group(1)), float(sz.group(2)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--dry-run', action='store_true', help='check and report only (no closed views needed, nothing rewritten)')
    ap.add_argument('--netlist-only', action='store_true',
                    help='rewrite die.v / place.tcl / pads / expand.json leaves even where a standard has no closed view yet '
                         '(LEF / libs untouched, RUN/case_kv/RLY_STD_NETLIST_ONLY written): port-bind checks only, never a '
                         'physical die run')
    a = ap.parse_args(argv)
    case, libs = a.run / 'case_kv', a.run / 'libs'
    rel = json.loads((a.run / 'relays.json').read_text())['masters']
    rev_bits = {m: sorted({i for lo, hi in r['reverse'] for i in range(lo, hi + 1)}) for m, r in rel.items()}
    lines = (case / 'die.v').read_text().split('\n')
    wires = {}
    for ln in lines:
        m = re.match(r'\s*wire\s+\[(\d+):0\]\s+(\S+);', ln)
        if m:
            wires[m.group(2)] = int(m.group(1)) + 1
    place = (case / 'place.tcl').read_text().split('\n')
    plc = {}
    for i, ln in enumerate(place):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', ln)
        if m:
            plc[m.group(1)] = (i, float(m.group(2)), float(m.group(3)), m.group(4))
    elef = (case / 'elements.lef').read_text()
    fsize = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in
             re.finditer(r'^MACRO (\S+)\s*$.*?\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', elef, re.M | re.S)}
    inst_re = re.compile(r'^\s+(qkd_rly_\w+) (\S+) \((.*)\);\s*$')
    new_lines, add_wires, add_place, drop = [], [], [], set()
    rep = dict(schema='opentallas.qwen_kvsys_rly_std.v1', standards={name(s): dict(w=STD[s][0], h=STD[s][1], bits=s) for s in STD},
               replica_gap_um=REPLICA_GAP, per_master={}, totals=defaultdict(int))
    used_std = defaultdict(int)
    instance_pads = {}
    hdom = grp_pc_hck_domains(lines, wires) if GRP_PC_HCK else {}
    if GRP_PC_HCK:
        rep['grp_pc_hck'] = dict(relays=len(hdom), hck_bits=sum(len(v[0]) for v in hdom.values()), split_relays={})
    for ln in lines:
        m = inst_re.match(ln)
        if not m:
            new_lines.append(ln)
            continue
        mst, inst, body = m.groups()
        conns = dict((c.group(1), c.group(2).strip()) for c in re.finditer(r'\.(\w+)\(([^()]*)\)', body))
        if set(conns) != {'a', 'b', 'ck'}:
            raise ValueError(f'{inst}: relay ports {sorted(conns)} != a / b / ck')
        A, B = net_bits(conns['a'], wires), net_bits(conns['b'], wires)
        W = rel[mst]['width']
        if len(A) != W or len(B) != W:
            raise ValueError(f'{inst}: a / b {len(A)} / {len(B)} b vs relay width {W}')
        rv = rev_bits[mst]
        bid = re.sub(r'^rly_', '', inst).rsplit('_', 1)[0]
        land = mst.endswith(LAND_SUFFIX)
        hb, hck_net = hdom.get(inst, (frozenset(), None))
        fwd = [i for i in range(W) if i not in set(rv)]
        split = None
        if hb:
            if hb & set(rv):
                raise ValueError(f'{inst}: OT_KV_GRP_PC_HCK hck bits {sorted(hb & set(rv))[:4]} are reverse bits')
            fwd = [i for i in fwd if i not in hb] + sorted(hb)     # ck replicas first, then the hck replicas
            split = (W - len(rv) - len(hb), len(hb))
        fw_, fh_, reps = layout(W, len(rv), land=land, split=split)
        if inst not in plc:
            raise ValueError(f'{inst}: not placed in place.tcl')
        _, fx, fy, fo = plc[inst]
        if fo not in FLIP:
            raise ValueError(f'{inst}: relay frame orient {fo}')
        flx, fly = FLIP[fo]
        frame = fsize.get(mst)
        fits = frame is not None and fw_ <= frame[0] + 0.05 and fh_ <= frame[1] + 0.05
        if not fits and not a.dry_run:
            raise ValueError(f'{inst}: frame {frame} of {mst} cannot hold the standard row {fw_} x {fh_} um '
                             f'(generate the case with OT_KV_RLY_STD=1; reverse slots reserved for {REV_BUS.pattern})')
        # a frame taller than the row (qkd_rly_2089: its pre-expansion abstract keeps the whole word on one M4 face)
        # centres the row on the frame's pin height
        oy = math.floor(max(0.0, frame[1] - fh_) / 2 / GY + 1e-9) * GY if fits else 0.0
        k_f, k_r = 0, 0
        n_ck_rep = len(replicas(split[0])) if split else None
        for j, (s, dx, dy, role) in enumerate(reps):
            nm = f'{inst}__s{j}'
            ck_ = conns['ck']
            if role == 'fwd' and split:
                # the ck part fills its own replicas only (never an hck bit in a ck replica, or the reverse)
                part = fwd[:split[0]] if j < n_ck_rep else fwd[split[0]:]
                off = k_f if j < n_ck_rep else k_f - split[0]
                idx = part[off:off + s]
                k_f += len(idx)
                if j >= n_ck_rep:
                    ck_ = hck_net
                    rep['grp_pc_hck']['split_relays'].setdefault(inst, []).append(nm)
            elif role == 'fwd':
                idx = fwd[k_f:k_f + s]
                k_f += len(idx)
                ain = [A[i] for i in idx] + ['0'] * (s - len(idx))
                bout = [B[i] for i in idx]
            else:
                idx = rv[k_r:k_r + s]                     # reverse bits: b -> flop -> a (mirrored replica)
                k_r += len(idx)
                ain = [B[i] for i in idx] + ['0'] * (s - len(idx))
                bout = [A[i] for i in idx]
            entry = replica_pads(s, len(idx))
            if entry is not None:
                instance_pads[nm] = entry
            if len(bout) < s:
                sp = f'n_{nm}__spare'
                add_wires.append(f'  wire [{s - len(bout) - 1}:0] {sp};')
                bout = bout + [f'{sp}[{t}]' for t in range(s - len(bout))]
            new_lines.append(f'  {name(s)} {nm} (.ck({ck_}), .a({pack(ain)}), .b({pack(bout)}));')
            # a mirrored frame (kv_pin_repair.py relays are MY: a on the E face) mirrors the row and every replica
            sw_, sh_ = dims(s, role, land)
            px = fw_ - dx - sw_ if flx else dx
            py = oy + (fh_ - dy - sh_ if fly else dy)
            if land and role == 'fwd':
                rep.setdefault('land_slots', {})[nm] = dict(frame=inst, S=s, outline=[sw_, sh_])
            ro = ORIENT[(flx ^ (role == 'rev'), fly)]
            add_place.append(f'ot_mts::place [$_blk findInst {nm}] {fx + px:.3f} {fy + py:.3f} {ro}')
            used_std[s] += 1
            rep['totals']['pad_bits'] += ain.count('0')
        if k_f != len(fwd) or k_r != len(rv):
            raise ValueError(f'{inst}: {k_f}/{len(fwd)} forward, {k_r}/{len(rv)} reverse bits placed')
        drop.add(inst)
        pm = rep['per_master'].setdefault(mst, dict(width=W, reverse=len(rv), replicas=[name(s) for s, *_ in reps],
                                                    row_um=[fw_, fh_], frame_um=list(frame) if frame else None,
                                                    frame_fits=fits, instances=0, landing=land))
        pm['instances'] += 1
        pm['frame_fits'] = pm['frame_fits'] and fits
        rep['totals']['relays'] += 1
        rep['totals']['replicas'] += len(reps)
    rep['totals'] = dict(rep['totals'], per_standard={name(s): n for s, n in sorted(used_std.items())},
                         std_area_mm2=round(sum(n * STD[s][0] * STD[s][1] for s, n in used_std.items()) / 1e6, 3),
                         frames_not_fitting=sum(1 for v in rep['per_master'].values() if not v['frame_fits']))
    pads = dict(pads={}, instances=instance_pads)
    rep['pads'] = pads
    if a.dry_run:
        out = a.run / 'rly_std.dry.json'
        out.write_text(json.dumps(rep, indent=1) + '\n')
        print(json.dumps(rep['totals']))
        return 0
    views = {}
    for s in used_std:
        vd = f'{RT}/{name(s)}/views/{name(s)}'
        lef = ROOT / vd / f'{name(s)}.lef'
        if not lef.exists():
            if a.netlist_only:
                continue
            raise FileNotFoundError(f'{name(s)}: no closed view {lef} (route the standard first)')
        blk, sz = lef_macro(lef)
        if abs(sz[0] - STD[s][0]) > 0.001 or abs(sz[1] - STD[s][1]) > 0.001:
            raise ValueError(f'{name(s)}: view {sz} != standard outline {STD[s]}')
        views[s] = (vd, blk, sz)
    k = max(i for i, ln in enumerate(new_lines) if re.match(r'\s*wire\b', ln))
    new_lines[k + 1:k + 1] = add_wires
    for f in ('die.v', 'place.tcl', 'elements.lef'):
        if not (case / f'{f}.prestd').exists():
            shutil.copy(case / f, case / f'{f}.prestd')
    (case / 'die.v').write_text('\n'.join(new_lines))
    keep = [ln for i, ln in enumerate(place) if not any(i == plc[x][0] for x in drop)]
    j = max(i for i, ln in enumerate(keep) if 'ot_mts::place' in ln)
    keep[j + 1:j + 1] = add_place
    (case / 'place.tcl').write_text('\n'.join(keep))
    add_lef = [views[s][1] for s in sorted(views) if not re.search(rf'^MACRO {name(s)}\s*$', elef, re.M)]
    t = elef.rstrip()
    end = re.search(r'^END LIBRARY\s*$', t, re.M)
    t = (t[:end.start()] + '\n'.join(add_lef) + '\n' + t[end.start():]) if end else t + '\n' + '\n'.join(add_lef) + '\n'
    (case / 'elements.lef').write_text(t + '\n')
    (case / 'die.v.pads.json').write_text(json.dumps(pads, indent=1) + '\n')
    vj = json.loads((libs / 'views.json').read_text())
    for s, (vd, _, sz) in sorted(views.items()):
        for c in CORNERS:
            src = ROOT / vd / f'{name(s)}_{c}.lib'
            if not src.exists():
                if c == 'ss':
                    continue
                raise FileNotFoundError(src)
            txt = re.sub(r'library\s*\(\s*"?[^")]+"?\s*\)', f'library (qfd_etm_{name(s)}_{c})', src.read_text(), count=1)
            (libs / f'qfd_etm_{name(s)}_{c}.lib').write_text(txt)
        vj['views'][name(s)] = dict(bound=True, view=vd, module=name(s), real_um=list(sz), cls='relay_standard',
                                    replaces=sorted(rep['per_master']))
    (libs / 'views.json').write_text(json.dumps(vj, indent=1) + '\n')
    ex = a.run / 'expand.json'
    ej = json.loads(ex.read_text()) if ex.exists() else dict(schema='opentallas.qwen_kvsys_expand.v1', frames={})
    ej.setdefault('leaves', {}).update({name(s): dict(view=f'{RT}/{name(s)}/views/{name(s)}', rtl=RTL) for s in used_std})
    if a.netlist_only:
        (case / 'RLY_STD_NETLIST_ONLY').write_text('kv_rly_std.py --netlist-only: standards without closed views: '
                                                  + ' '.join(name(s) for s in sorted(set(used_std) - set(views))) + '\n')
    ex.write_text(json.dumps(ej, indent=1) + '\n')
    (a.run / 'rly_std.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(dict(removed=len(drop), added=len(add_place), **rep['totals'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
