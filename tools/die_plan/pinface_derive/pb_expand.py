"""DIE-QC-97 SU-RS-1 scoring aid (model only, never a plan of record): expand every bit_route per_bit internal_stations
chain of the su_l types into one entry per bit along the exact kit path (taps.per_bit_station_sites / kit_istations
is_bits: face pin -> L corner (leg_order) -> leaf_um, stations at L*(k+1)/(n+1)), so route_supply's station RUDY sees the
real per-bit legs instead of the chain-level regs_um polyline.  usage (cwd SRC): pb_expand.py SRC PLAN OUT [TYPES]"""
import copy, json, sys
from pathlib import Path
SRC, PL, OUT = sys.argv[1:4]
sys.path.insert(0, SRC + '/tools/die_plan')
import schema, gen_phys, taps
import os
CHAN = {}
for it in filter(None, os.environ.get('PB_CHAN', '').split(';')):
    tn_, f_, lo_, hi_ = it.split(':'); CHAN[(tn_, f_)] = (float(lo_), float(hi_))

TOL = 0.5
def seg_clear(MR, a, b):
    x0, x1 = sorted((a[0], b[0])); y0, y1 = sorted((a[1], b[1]))
    return not any(x0 < r[2] - TOL and x1 > r[0] + TOL and y0 < r[3] - TOL and y1 > r[1] + TOL for r in MR)
def clear_col(MR, px, py, ly, want):
    """the channel column nearest to want whose two new legs (px,py)->(xc,py)->(xc,ly) stay off every hard core; None = keep the L"""
    step = 2.16 if want > px else -2.16
    xc = want
    while (xc - px) * step > 0:
        if seg_clear(MR, (px, py), (xc, py)) and seg_clear(MR, (xc, py), (xc, ly)):
            return xc
        xc -= step
    return None
raw = json.load(open(PL)); P = schema.Plan(copy.deepcopy(raw), path=PL)
types = sys.argv[4].split(',') if len(sys.argv) > 4 else [t for t in raw['partition_types'] if '_su_l' in t]
tot = {}
for tn in types:
    t = raw['partition_types'][tn]
    pins = gen_phys.type_pins(P, tn)
    at = {}
    for name, bit, _ln, x, y, face in pins:
        at.setdefault(name, {})[bit] = (x, y, face)
    buses = {b['name']: b for b in t.get('buses', [])}
    new = []; nb = 0; nz = 0; WH = [0.0]; XM = [0]
    MR = [(h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['outline_um'][1]) for h in t.get('hard_cores', [])]
    for e in t.get('internal_stations', []):
        if e.get('bit_route') != 'per_bit' or not e.get('conn', '').startswith('bus:') or e.get('bit_sites_um'):
            new.append(e); continue
        bus = e['conn'][4:]; lx, ly = e['leaf_um']; n = len(e['regs_um'])
        bat = at.get(bus, {})
        if e.get('start_core'):
            su = e['start_um']; f0 = next(iter(bat.values()))[2] if bat else buses[bus]['face']
            bat = {bit: (float(p[0]), float(p[1]), f0) for bit, p in enumerate(su)}
        d_in = buses[bus]['dir'] == 'in'
        keep = set(int(b) for b in e['core_bits']) if e.get('core') else None
        along = e.get('leg_order', 'normal_first') == 'along_first'
        if os.environ.get('PB_LEG') == 'normal': along = False
        if os.environ.get('PB_LEG') == 'along': along = True
        if os.environ.get('PB_LEG') == 'flip': along = not along
        for bit, (px, py, face) in sorted(bat.items()):
            if keep is not None and bit not in keep and bit != len(bat) - 1:
                continue
            cx, cy = (lx, py) if (face in ('E', 'W')) != along else (px, ly)
            path = [(px, py), (cx, cy), (lx, ly)]
            if e.get('leg_order') == 'channel':   # KIT-CHAN-1 geometry
                import istation_channel as IC
                path = IC.path(px, py, lx, ly, face, 'in' if str(e.get('launch', '')).startswith('face') else 'out',
                               IC.column(*IC.entry_channel(e), bit, max(bat) + 1))   # kit: nbits = bound W + 1
            ch = CHAN.get((tn, face)) or CHAN.get(('*', face))
            if ch and along and face in ('E', 'W'):     # WHAT-IF: Z route, vertical leg in a channel column spread by bit
                want = ch[0] + (ch[1] - ch[0]) * ((bit + 0.5) / max(1, len(bat)))
                xc = clear_col(MR, px, py, ly, want)
                if xc is not None:
                    path = [(px, py), (xc, py), (xc, ly), (lx, ly)]
                    nz += 1
            pts = path if d_in else path[::-1]
            L = sum(abs(a_[0] - c_[0]) + abs(a_[1] - c_[1]) for a_, c_ in zip(pts, pts[1:]))
            regs = [list(taps._point_at(pts, L * (k + 1) / (n + 1))) for k in range(n)]
            f = dict(e); f.update(from_um=list(pts[0]), to_um=list(pts[-1]), regs_um=regs, bits=1, launch=f'{e.get("launch")}#b{bit}')
            for k_ in ('core_bits', 'bit_route', 'start_um', 'start_core', 'start_port'):
                f.pop(k_, None)
            f['core_bits'] = [bit] if e.get('core') else None
            if f['core_bits'] is None: f.pop('core_bits')
            new.append(f); nb += 1
            hop = L / (n + 1); WH[0] = max(WH[0], hop)
            if not (seg_clear(MR, path[0], path[1]) and all(seg_clear(MR, u, v) for u, v in zip(path[1:], path[2:]))): XM[0] += 1
    t['internal_stations'] = new; tot[tn] = (nb, nz, round(WH[0], 1), XM[0])
Path(OUT).write_text(json.dumps(raw))
print('expanded per-bit entries', tot)
