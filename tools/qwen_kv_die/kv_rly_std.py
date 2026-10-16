#!/usr/bin/env python3
"""Q-KVSYS-RLY 2026-10-16 (owner rule 19:50 PT 10-15 'fewer distinct tiles'; VIS-ROM QKV-04): KV/system die RELAY STANDARDS.

The KV die generator emits one relay master per bus width, qkd_rly_<W> (21 masters, 8,276 instances in kvs11-v143c), each
an unrouted frame whose pins sit on M4 at minimum pitch (20.9 pins/um).  With OT_KV_RLY_STD=1 every relay stage binds to
replicas of FOUR hardened standards (rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv, kits physical/ref_tile/qkd_rlys_<S>):

    qkd_rlys_1    10.8  x 10.8 um     1 b   (reset / boot tree hops qkd_rly_t1, 1-bit words, reverse bits)
    qkd_rlys_36   10.8  x 10.8 um    36 b
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
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RT = 'physical/ref_tile'
RTL = 'rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv'
STD = {1: (10.8, 10.8), 36: (10.8, 10.8), 296: (21.6, 47.52), 528: (21.6, 82.08)}
REPLICA_GAP = 10.8
GY = 2.16
CORNERS = ('tt', 'ff', 'ss')
FLIP = dict(R0=(0, 0), MX=(0, 1), MY=(1, 0), R180=(1, 1))
# buses whose die direction model carries reverse bits (kvs11-v143c relays.json: kvn 1048 / hb 284 / emf 289 / emr 521, one
# bit each): their frames reserve one qkd_rlys_1 slot; the netlist pass refuses a relay with more reverse bits than reserved
REV_BUS = re.compile(r'^(kvn|hb|emf|emr)(?:_|$)')
# replica choice: minimum (outline area + PAD_COST per tied bit + INST_COST per instance), at most 5 replicas
PAD_COST, INST_COST = 1.0, 60.0


def name(s):
    return f'qkd_rlys_{s}'


def replicas(w):
    """standard widths for a w-bit forward word, widest first (deterministic)"""
    if w <= 0:
        return []
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


def layout(w, rev=0):
    """(frame w, frame h, [(std, dx, dy, role)]) of a w-bit relay stage with rev reverse bits"""
    reps = [(s, 'fwd') for s in replicas(w - rev)] + [(1, 'rev')] * rev
    fh = max(STD[s][1] for s, _ in reps)
    out, x = [], 0.0
    for s, role in reps:
        dy = round(math.floor((fh - STD[s][1]) / 2 / GY + 1e-9) * GY, 4)
        out.append((s, round(x, 4), dy, role))
        x += STD[s][0] + REPLICA_GAP
    return round(x - REPLICA_GAP, 4), fh, out


def frame_rev(bid):
    return 1 if REV_BUS.match(bid) else 0


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
    min_used = {}
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
        fw_, fh_, reps = layout(W, len(rv))
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
        fwd = [i for i in range(W) if i not in set(rv)]
        k_f, k_r = 0, 0
        for j, (s, dx, dy, role) in enumerate(reps):
            nm = f'{inst}__s{j}'
            if role == 'fwd':
                idx = fwd[k_f:k_f + s]
                k_f += len(idx)
                ain = [A[i] for i in idx] + ['0'] * (s - len(idx))
                bout = [B[i] for i in idx]
                min_used[s] = min(min_used.get(s, s), len(idx))
            else:
                i = rv[k_r]
                k_r += 1
                ain, bout = [B[i]], [A[i]]                # reverse bit: b -> flop -> a
                min_used[1] = min(min_used.get(1, 1), 1)
            if len(bout) < s:
                sp = f'n_{nm}__spare'
                add_wires.append(f'  wire [{s - len(bout) - 1}:0] {sp};')
                bout = bout + [f'{sp}[{t}]' for t in range(s - len(bout))]
            new_lines.append(f'  {name(s)} {nm} (.ck({conns["ck"]}), .a({pack(ain)}), .b({pack(bout)}));')
            # a mirrored frame (kv_pin_repair.py relays are MY: a on the E face) mirrors the row and every replica
            px = fw_ - dx - STD[s][0] if flx else dx
            py = oy + (fh_ - dy - STD[s][1] if fly else dy)
            add_place.append(f'ot_mts::place [$_blk findInst {nm}] {fx + px:.3f} {fy + py:.3f} {fo}')
            used_std[s] += 1
            rep['totals']['pad_bits'] += ain.count('0')
        if k_f != len(fwd) or k_r != len(rv):
            raise ValueError(f'{inst}: {k_f}/{len(fwd)} forward, {k_r}/{len(rv)} reverse bits placed')
        drop.add(inst)
        pm = rep['per_master'].setdefault(mst, dict(width=W, reverse=len(rv), replicas=[name(s) for s, *_ in reps],
                                                    row_um=[fw_, fh_], frame_um=list(frame) if frame else None,
                                                    frame_fits=fits, instances=0))
        pm['instances'] += 1
        pm['frame_fits'] = pm['frame_fits'] and fits
        rep['totals']['relays'] += 1
        rep['totals']['replicas'] += len(reps)
    rep['totals'] = dict(rep['totals'], per_standard={name(s): n for s, n in sorted(used_std.items())},
                         std_area_mm2=round(sum(n * STD[s][0] * STD[s][1] for s, n in used_std.items()) / 1e6, 3),
                         frames_not_fitting=sum(1 for v in rep['per_master'].values() if not v['frame_fits']))
    pads = {name(s): dict(reason='KV relay standard used below its width (kv_rly_std.py): spare input bits tied low; '
                                 'the matching output bits drive private open wires', ports={'a': [[u, s - 1]]})
            for s, u in sorted(min_used.items()) if u < s}
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
    (case / 'die.v.pads.json').write_text(json.dumps(dict(pads=pads), indent=1) + '\n')
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
    ej.setdefault('leaves', {}).update({name(s): dict(view=views[s][0], rtl=RTL) for s in views})
    ex.write_text(json.dumps(ej, indent=1) + '\n')
    (a.run / 'rly_std.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(dict(removed=len(drop), added=len(add_place), **rep['totals'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
