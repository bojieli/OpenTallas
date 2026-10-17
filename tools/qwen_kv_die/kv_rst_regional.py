#!/usr/bin/env python3
"""KVPLAN 1815 (2026-10-16, COORDINATOR STANDARD items 1-2; owner direction 18:45 'regional synchronous reset trees, not
die-wide reset nets'): REGIONAL REGISTERED RESET TREES ON THE FLATTENED KV/SYSTEM DIE.

kv_die.py (OT_KV_RST_REGIONAL=1) plans each HOST reset / boot root only as far as one express relay chain per
OT_KV_RST_REGION_BOX region (the last stage = the region's qkd_rst_region, v1.4.3 release calendar unchanged); the
region is then ONE fan-out net.  After kv_expand.py flattened the wires-only frames into their closed leaves, this pass
re-plans every reset / boot fan-out net (n_rst_* / n_hboot*) whose loads are not all within one station hop as a LOCAL
REGISTERED TREE of qkd_rlys_1 stations (the closed 1-bit relay standard; one flop, no reset, one core cycle a hop) placed
in the FREE SPACE of the flattened die (inside a flattened frame between its leaves, or in the die channels), never over
an instance: kv_child_rst.plan -- each load pin <= LEAF_R um from its station (<= FAN loads a station), every hop
(driver -> station, station -> station) <= HOP um, nearest-first tree.  Each load's added depth is recorded
(RUN/rst_regional.json) and the region depth checked against RELAY_FLUSH (kv_die: reset release waits >= 128 core cycles
after the clock runs; the region roots hold reset while their chain is unflushed).

Excluded loads stay on the region net (reported): OT_KV_RST_EXCLUDE (regex on the load's master; default the PV16 pair
leaves -- their in-array distribution is the PV pair successor's).

    kv_rst_regional.py --run RUN
rewrites RUN/case_kv/{die.v, place.tcl, elements.lef} (originals kept as *.prerst), adds the qkd_rlys_1 closed view to
RUN/libs + views.json + expand.json leaves, writes RUN/rst_regional.json.
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_child_rst as CR          # noqa: E402
import kv_rly_std as RS            # noqa: E402  (net_bits, pack, lef_macro, RTL, RT)

RST_NET = re.compile(r'^n_(rst_|hboot)')
RELAY = re.compile(r'^(qkd_rly_|qkd_rlys_|qkd_rst_region$)')
EXCLUDE = re.compile(os.environ.get('OT_KV_RST_EXCLUDE', r'^ot_qwen_tp8_pv_'))
WIN = 240.0
STATION = 'qkd_rlys_1'
CORNERS = ('tt', 'ff', 'ss')


def lef_all(text):
    size, pins, dirs = {}, defaultdict(dict), defaultdict(dict)
    cur = pin = None
    for ln in text.split('\n'):
        s = ln.strip()
        if s.startswith('MACRO '):
            cur, pin = s.split()[1], None
        elif cur and s.startswith('SIZE') and cur not in size:
            t = s.split()
            size[cur] = (float(t[1]), float(t[3]))
        elif cur and s.startswith('PIN '):
            pin = s.split()[1]
        elif pin and s.startswith('DIRECTION'):
            dirs[cur][pin] = s.split()[1].rstrip(';')
        elif pin and s.startswith('RECT') and pin not in pins[cur]:
            t = s.split()
            pins[cur][pin] = ((float(t[1]) + float(t[3])) / 2, (float(t[2]) + float(t[4])) / 2)
        elif pin and s.startswith('END ') and s.split()[1] == pin:
            pin = None
    return size, pins, dirs


def net_bits(expr, wires):
    """die net expression -> bit refs LSB first (concatenations, slices, constants as 'CONST')"""
    parts = [x.strip() for x in expr.strip()[1:-1].split(',') if x.strip()] if expr.strip().startswith('{') else [expr.strip()]
    out = []
    for p in reversed(parts):
        b = re.fullmatch(r'(\S+)\[(\d+)(?::(\d+))?\]', p)
        if b:
            hi = int(b.group(2))
            lo = int(b.group(3)) if b.group(3) else hi
            out += [f'{b.group(1)}[{i}]' for i in range(lo, hi + 1)]
        elif re.fullmatch(r"\d+'[bh][0-9a-fA-F_]+", p):
            raise ValueError(f'constant literal in a die connection: {p}')
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
    parts = [n if lo is None else (f'{n}[{lo}]' if lo == hi else f'{n}[{hi}:{lo}]') for n, lo, hi in reversed(runs)]
    return parts[0] if len(parts) == 1 else '{' + ', '.join(parts) + '}'


def die_xy(x0, y0, w, h, o, p):
    px, py = p
    return {'R0': (x0 + px, y0 + py), 'MX': (x0 + px, y0 + h - py), 'MY': (x0 + w - px, y0 + py),
            'R180': (x0 + w - px, y0 + h - py)}[o]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    a = ap.parse_args(argv)
    case, libs = a.run / 'case_kv', a.run / 'libs'
    vd = f'{RS.RT}/{STATION}/views/{STATION}'
    st_lef = ROOT / vd / f'{STATION}.lef'
    st_blk, st_sz = RS.lef_macro(st_lef)
    if abs(st_sz[0] - CR.STN) > 1e-3 or abs(st_sz[1] - CR.STN) > 1e-3:
        raise ValueError(f'{STATION} view {st_sz} != {CR.STN}')
    elef = (case / 'elements.lef').read_text()
    size, pins, dirs = lef_all(elef + '\n' + st_blk)
    lines = (case / 'die.v').read_text().split('\n')
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
    pos = {}
    for ln in place:
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', ln)
        if m:
            pos[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    inst_re = re.compile(r'^(\s+)(\w+) (\S+) \((.*)\);\s*$')
    insts = {}                                  # name -> [line idx, master, [(port, refs)]]
    bitpins = defaultdict(list)                 # reset bit ref -> [(inst, port, bit index)]
    rects = {}
    for li, ln in enumerate(lines):
        m = inst_re.match(ln)
        if not m or m.group(2) in ('wire', 'assign', 'module'):
            continue
        _, mst, nm, body = m.groups()
        conns = []
        for c in re.finditer(r'\.(\\?\S+?)\((\{[^}]*\}|[^)]*)\)', body):
            refs = net_bits(c.group(2).strip(), wires)
            conns.append([c.group(1), refs])
            for i, r in enumerate(refs):
                if RST_NET.match(r.rsplit('[', 1)[0]):
                    bitpins[r].append((nm, len(conns) - 1, i))
        insts[nm] = [li, mst, conns]
        if nm in pos and mst in size:
            x, y, _ = pos[nm]
            rects[nm] = (x, y, x + size[mst][0], y + size[mst][1])
    die_w = max(r[2] for r in rects.values())
    die_h = max(r[3] for r in rects.values())

    def pin_of(nm, ci, i):
        mst = insts[nm][1]
        p, refs = insts[nm][2][ci]
        key = f'{p}[{i}]' if f'{p}[{i}]' in pins[mst] else p
        q = pins[mst].get(key)
        if q is None or nm not in pos:
            return None, None
        x, y, o = pos[nm]
        w, h = size[mst]
        return die_xy(x, y, w, h, o, q), dirs[mst].get(key, dirs[mst].get(p))
    rep = dict(schema='opentallas.qwen_kvsys_rst_regional.v1', hop_um=CR.HOP, leaf_um=CR.LEAF_R, fan=CR.FAN,
               nets={}, stations=0, excluded_loads=defaultdict(int), kept_nets=0, far_loads=[])
    add_lines, add_wires, add_place = [], [], []
    touched = set()
    gst = {}                                   # placed stations (keep-outs for later nets)
    for ref in sorted(bitpins):
        ends = bitpins[ref]
        drv, loads = None, []
        for nm, ci, i in ends:
            mst = insts[nm][1]
            p = insts[nm][2][ci][0]
            xy, d = pin_of(nm, ci, i)
            is_out = (RELAY.match(mst) and p == 'b') or d == 'OUTPUT' or (nm == 'host' and d != 'INPUT')
            if is_out and drv is None and not (RELAY.match(mst) and p == 'a'):
                drv = (nm, ci, i, xy)
            else:
                loads.append((nm, ci, i, xy, mst))
        if drv is None or drv[3] is None:
            continue
        # every load counts: a chain's next relay ('a' pin) too -- a reset hop over HOP or an inner tree node whose
        # child chains' first relays spread over > HOP (kvs13j n_rst_die_t8_0: 7 first relays over 1.27 mm) gets stations
        true_loads = [L for L in loads if L[3] is not None]
        if not true_loads:
            continue
        keep = [L for L in true_loads if EXCLUDE.match(L[4]) or L[3] is None]
        mov = [L for L in true_loads if L not in keep]
        for L in keep:
            rep['excluded_loads'][L[4]] += 1
        if not mov:
            continue
        dxy = drv[3]
        rad = max(abs(L[3][0] - dxy[0]) + abs(L[3][1] - dxy[1]) for L in mov)
        if rad <= CR.HOP and len(mov) <= CR.FAN:
            rep['kept_nets'] += 1
            continue
        xs = [dxy[0]] + [L[3][0] for L in mov]
        ys = [dxy[1]] + [L[3][1] for L in mov]
        win = (max(0.0, min(xs) - WIN), max(0.0, min(ys) - WIN), min(die_w, max(xs) + WIN), min(die_h, max(ys) + WIN))
        obs = [r for n, r in rects.items() if r[0] < win[2] and r[2] > win[0] and r[1] < win[3] and r[3] > win[1]]
        obs += [r for r in gst.values() if r[0] < win[2] and r[2] > win[0] and r[1] < win[3] and r[3] > win[1]]
        dnm = drv[0]
        ck = next((refs[0] for p, refs in insts[dnm][2] if p == 'ck'), None) or 'n_clk_core_c[0]'
        net = ref.rsplit('[', 1)[0]
        base = re.sub(r'[^A-Za-z0-9_]', '_', ref)
        st, assign = CR.plan(f'rrs_{base}', win, obs, [((L[0], L[1], L[2]), L[3]) for L in mov], dxy, lambda pt: ck)
        for s_ in st:
            wn = f'n_{s_["name"]}'
            add_wires.append(f'  wire [0:0] {wn};')
            a_ = ref if s_['parent'] is None else f'n_{s_["parent"]}[0]'
            add_lines.append(f'  {STATION} {s_["name"]} (.ck({ck}), .a({a_}), .b({wn}[0]));')
            add_place.append(f'ot_mts::place [$_blk findInst {s_["name"]}] {s_["x"]:.3f} {s_["y"]:.3f} R0')
            gst[s_['name']] = (s_['x'], s_['y'], s_['x'] + CR.STN, s_['y'] + CR.STN)
        depth = {s_['name']: s_['depth'] for s_ in st}
        leaf_r = 0.0
        sxy = {s_['name']: (s_['x'] + CR.STN / 2, s_['y'] + CR.STN / 2) for s_ in st}
        far_st = {s_['name'] for s_ in st if s_.get('far')}
        for (nm, ci, i), sname in assign.items():
            insts[nm][2][ci][1][i] = f'n_{sname}[0]'
            touched.add(nm)
            L = next(L_ for L_ in mov if (L_[0], L_[1], L_[2]) == (nm, ci, i))
            dl_ = abs(L[3][0] - sxy[sname][0]) + abs(L[3][1] - sxy[sname][1])
            if sname in far_st:
                rep['far_loads'].append(dict(net=ref, load=f'{nm}.{insts[nm][2][ci][0]}', master=L[4], um=round(dl_, 1)))
            else:
                leaf_r = max(leaf_r, dl_)
        rep['nets'][ref] = dict(driver=dnm, loads=len(mov), kept_excluded=len(keep), radius_before_um=round(rad, 1),
                                stations=len(st), max_depth=max(depth.values()), max_hop_um=max(s_['hop_um'] for s_ in st),
                                max_leaf_um=round(leaf_r, 1))
        rep['stations'] += len(st)
        print(f'{ref}: {len(mov)} loads r {rad:.0f} -> {len(st)} stations depth {max(depth.values())}', file=sys.stderr)
    if not rep['stations']:
        print('kv_rst_regional: nothing to re-plan')
    for nm in touched:
        li, mst, conns = insts[nm]
        ind = re.match(r'^(\s+)', lines[li]).group(1)
        lines[li] = f'{ind}{mst} {nm} ({", ".join(f".{p}({pack(refs)})" for p, refs in conns)});'
    k = max(i for i, ln in enumerate(lines) if re.match(r'\s*wire\b', ln))
    lines[k + 1:k + 1] = add_wires
    e = max(i for i, ln in enumerate(lines) if re.match(r'\s*endmodule\b', ln))
    lines[e:e] = add_lines
    for f in ('die.v', 'place.tcl', 'elements.lef'):
        if not (case / f'{f}.prerst').exists():
            shutil.copy(case / f, case / f'{f}.prerst')
    (case / 'die.v').write_text('\n'.join(lines))
    j = max(i for i, ln in enumerate(place) if 'ot_mts::place' in ln)
    place[j + 1:j + 1] = add_place
    (case / 'place.tcl').write_text('\n'.join(place))
    if rep['stations'] and not re.search(rf'^MACRO {STATION}\s*$', elef, re.M):
        t = elef.rstrip()
        end = re.search(r'^END LIBRARY\s*$', t, re.M)
        t = (t[:end.start()] + st_blk + '\n' + t[end.start():]) if end else t + '\n' + st_blk + '\n'
        (case / 'elements.lef').write_text(t + '\n')
    if rep['stations']:
        for c in CORNERS:
            src = ROOT / vd / f'{STATION}_{c}.lib'
            if not src.exists():
                if c == 'ss':
                    continue
                raise FileNotFoundError(src)
            txt = re.sub(r'library\s*\(\s*"?[^")]+"?\s*\)', f'library (qfd_etm_{STATION}_{c})', src.read_text(), count=1)
            (libs / f'qfd_etm_{STATION}_{c}.lib').write_text(txt)
        vj = json.loads((libs / 'views.json').read_text())
        vj['views'][STATION] = dict(bound=True, view=vd, module=STATION, real_um=list(st_sz), cls='relay_standard')
        (libs / 'views.json').write_text(json.dumps(vj, indent=1) + '\n')
        ex = a.run / 'expand.json'
        ej = json.loads(ex.read_text()) if ex.exists() else dict(schema='opentallas.qwen_kvsys_expand.v1', frames={})
        ej.setdefault('leaves', {})[STATION] = dict(view=vd, rtl=RS.RTL)
        ex.write_text(json.dumps(ej, indent=1) + '\n')
    rep['excluded_loads'] = dict(rep['excluded_loads'])
    rep['max_depth'] = max((v['max_depth'] for v in rep['nets'].values()), default=0)
    rep['max_hop_um'] = max((v['max_hop_um'] for v in rep['nets'].values()), default=0)
    rep['max_leaf_um'] = max((v['max_leaf_um'] for v in rep['nets'].values()), default=0)
    (a.run / 'rst_regional.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(dict({k_: rep[k_] for k_ in ('stations', 'max_depth', 'max_hop_um', 'max_leaf_um', 'kept_nets', 'excluded_loads')},
                          far_loads=len(rep['far_loads']), far_masters=sorted({f['master'] for f in rep['far_loads']}))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
