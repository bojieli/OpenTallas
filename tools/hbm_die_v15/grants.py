#!/usr/bin/env python3
"""HBM v15.x top-down outline + pin grants on the ADOPTED floorplan T_band2__npg4_s5 (coordinator 2026-10-15 ~09:25,
GLOBAL-FP-H main 952c5933c, results/arch/hbm_globalfp_1015/noatt/pins/).

    grants.py --synth DIR [--out results/arch/hier_contract_1015/hbm_v15.json]

Writes a schema opentallas.hier_contract.v1 die contract (die "hbm_v15") whose slots are the grants that the v15 masters'
kits are checked against by tools/hier_contract/slot_fit.py (outline, pin faces/layers, clock entry):
  * homes  = the adopted floorplan block (GLOBAL-FP-H box) when it holds the measured block, else the nearest free
             rectangle (occupancy of all 187 adopted blocks + every grant already made) -- every move is recorded with
             its reason in `relocations`;
  * outline = max(floorplan box, measured need).  Need = synthesised std area (tools/hbm_die_v15/synth_master.sh, ASAP7
             RVT TT) / 0.50 + mapped-macro area x 1.25 (halo), and per face: bits x 0.096 um (2 tracks / bit on M4 E/W,
             M5 N/S) <= 0.60 of the face (owner cut rule);
  * pins   = every RTL port of the master on the face where the adopted floorplan routes that port's link (peer block),
             packed in floorplan order, offsets in the master's R0 frame; ports whose peer the source contract leaves
             unbound get the face of their declared producer/consumer class (CONTROL face = clock entry face) and are
             listed under `pins_on_unbound_ports` -- they are grants for the join, not a claim the join exists.
No stub, no pin-only master: a slot names a real RTL master + source, or (whole-SU, SFU port groups) is a REQUEST slot
with `rtl_pending` naming the owner; a request slot has no cell a kit could fit until the owner's RTL lands.
"""
import argparse, hashlib, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_die_views as views  # noqa: E402

FP = 'results/arch/hbm_globalfp_1015/noatt/pins/T_band2__npg4_s5.pins.json'
CONTRACT = 'results/arch/hbm_die_v15/source_contract/contract.json'
STEP = 0.096          # um per bit on one layer (2 x 0.048 tracks)
FACE_CAP = 0.60       # owner cut rule
GRID = 2.16           # outline / origin grid (ASAP7 row x 8 = site multiple used by every v15 kit)
STD_UTIL = 0.50
HALO = 1.25
FACE_LAYER = dict(N='M5', S='M5', E='M4', W='M4')
OPP = dict(N='S', S='N', E='W', W='E')
SID = ('SW', 'SE', 'NW', 'NE')
MACRO_UM2 = {  # from LEF SIZE (physical/asap7_memory_macros*/<m>/<m>.lef)
}


def snap(v):
    return round(math.ceil(v / GRID - 1e-9) * GRID, 3)


def macro_area(name):
    if name in MACRO_UM2:
        return MACRO_UM2[name]
    for base in ('physical/asap7_memory_macros_v2', 'physical/asap7_memory_macros'):
        lef = ROOT / base / name / f'{name}.lef'
        if lef.exists():
            m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef.read_text())
            if m:
                MACRO_UM2[name] = (float(m.group(1)), float(m.group(2)))
                return MACRO_UM2[name]
    raise SystemExit(f'no LEF for macro {name}')


def synth(sdir, name):
    """{std_um2, macros:{name:count}} from <sdir>/<name>/<name>.stat (+ .hier.stat for macro instances)"""
    st = Path(sdir) / name / f'{name}.stat'
    if not st.exists():
        return None
    t = st.read_text()
    m = re.search(r'Chip area for top module .*?:\s*([\d.]+)', t) or re.search(r'Chip area for module .*?:\s*([\d.]+)', t)
    macros = {}
    for mm in re.finditer(r'^\s*(\d+)\s+(?:\S+\s+)?(ot_sram_\w+)\s*$', t, re.M):
        macros[mm.group(2)] = macros.get(mm.group(2), 0) + int(mm.group(1))
    ff = sum(int(x) for x in re.findall(r'^\s*(\d+)\s+DFF\w*', t, re.M))
    return dict(std_um2=float(m.group(1)) if m else None, macros=macros, ff=ff, stat=str(st))


class Occ:
    def __init__(self, W, H):
        self.W, self.H, self.r = W, H, []

    def add(self, name, x, y, w, h):
        self.r.append((name, x, y, w, h))

    def free(self, x, y, w, h, ignore=(), gap=20.0):
        if x < 20 or y < 20 or x + w > self.W - 20 or y + h > self.H - 20:
            return False
        for n, a, b, c, d in self.r:
            if n in ignore:
                continue
            if x < a + c + gap and a < x + w + gap and y < b + d + gap and b < y + h + gap:
                return False
        return True

    def near(self, cx, cy, w, h, ignore=(), step=43.2, limit=12000):
        """free rectangle whose centre is nearest (cx, cy), spiral search on a 43.2 um lattice"""
        best = None
        r = 0.0
        while r <= limit:
            n = max(1, int(2 * math.pi * r / step))
            for k in range(n):
                a = 2 * math.pi * k / n
                x, y = snap(cx + r * math.cos(a) - w / 2), snap(cy + r * math.sin(a) - h / 2)
                if self.free(x, y, w, h, ignore):
                    d = math.hypot(x + w / 2 - cx, y + h / 2 - cy)
                    if best is None or d < best[0]:
                        best = (d, x, y)
            if best:
                return best[1], best[2]
            r += step
        raise SystemExit(f'no free {w}x{h} near {cx},{cy}')


def face_toward(box, px, py):
    cx, cy = box['x'] + box['w'] / 2, box['y'] + box['h'] / 2
    dx, dy = px - cx, py - cy
    if abs(dx) / max(box['w'], 1) >= abs(dy) / max(box['h'], 1):
        return 'E' if dx > 0 else 'W'
    return 'N' if dy > 0 else 'S'


def place_pins(outline, faces_ports, clock_ports, ctl_face):
    """faces_ports: {face: [(port, bits, anchor_offset or None)]} -> pins list; grows outline if a face exceeds FACE_CAP"""
    w, h = outline
    for f, ps in faces_ports.items():
        need = sum(b for _, b, _ in ps) * STEP / FACE_CAP + 10.0
        if f in 'NS' and need > w:
            w = snap(need)
        if f in 'EW' and need > h:
            h = snap(need)
    pins, util = [], {}
    for f, ps in faces_ports.items():
        L = w if f in 'NS' else h
        used = sum(b for _, b, _ in ps) * STEP
        util[f] = round(used / L, 3)
        # pack in anchor order, starting so that the packed run is centred on the mean anchor (or the face centre)
        ps = sorted(ps, key=lambda p: (p[2] if p[2] is not None else L / 2))
        anchors = [p[2] for p in ps if p[2] is not None]
        centre = (sum(anchors) / len(anchors)) if anchors else L / 2
        lo = min(max(5.0, centre - used / 2), max(5.0, L - 5.0 - used))
        cur = lo
        for port, bits, _ in ps:
            span = bits * STEP
            nm = f'{port}[{bits - 1}:0]' if bits > 1 else port
            pins.append(dict(name=nm, face=f, layer=FACE_LAYER[f], offset=round(cur + span / 2, 3),
                             span_um=[round(cur, 3), round(cur + span, 3)], pins_per_um=round(1 / STEP, 3)))
            cur += span
    clk = sorted(clock_ports)[0] if clock_ports else None
    entry = None
    if clk:
        p = next(p for p in pins if p['name'].split('[')[0] == clk)
        entry = dict(pin=clk, face=p['face'], layer=p['layer'], offset=p['offset'])
    return (w, h), pins, util, entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--synth', required=True)
    ap.add_argument('--out', default='results/arch/hier_contract_1015/hbm_v15.json')
    a = ap.parse_args()
    fp = json.loads((ROOT / FP).read_text())
    con = json.loads((ROOT / CONTRACT).read_text())
    W, H = fp['die_outline_um']
    B = fp['blocks']
    occ = Occ(W, H)
    for k, v in B.items():
        occ.add(k, v['x'], v['y'], v['w'], v['h'])
    inst = con['instances']

    def ports_of(i):
        p = inst[i]['ports']
        p = json.loads(p) if isinstance(p, str) else p
        return {k: (v['direction'], v['bits']) for k, v in p.items()}

    def ports_src(path, top, params=None):
        return views.L.parse_module(path, top, params or {})['ports']

    def link_anchor(block, peer_prefix, cls=None):
        """(face, offset) of the floorplan link between block and a peer (prefix match), first hit"""
        hits = []
        for f, x in B[block]['faces'].items():
            for p in x['pins']:
                if p['peer'].startswith(peer_prefix) and (cls is None or p['cls'] == cls):
                    hits.append((f, p['offset_um'] + p['span_um'] / 2, p['bits']))
        if not hits:
            return None
        # the face carrying most bits to that peer class
        agg = {}
        for f, o, b in hits:
            agg.setdefault(f, []).append((o, b))
        f = max(agg, key=lambda k: sum(b for _, b in agg[k]))
        os_ = agg[f]
        return f, sum(o * b for o, b in os_) / sum(b for _, b in os_)

    slots, reloc, report = [], [], {}
    sub_layouts = {}

    def need_outline(sy, box_wh, min_wh=(0, 0)):
        std = (sy or {}).get('std_um2') or 0.0
        mac = sum(c * macro_area(m)[0] * macro_area(m)[1] for m, c in ((sy or {}).get('macros') or {}).items())
        area = std / STD_UTIL + mac * HALO
        bw, bh = box_wh
        if bw * bh >= area:
            return (snap(max(bw, min_wh[0])), snap(max(bh, min_wh[1]))), area
        s = math.sqrt(area / (bw * bh))
        return (snap(max(bw * s, min_wh[0])), snap(max(bh * s, min_wh[1]))), area

    def home(name, block, wh, prefer=None):
        """origin: the floorplan block's origin if the grown outline still fits there, else nearest free spot"""
        if block in B:
            b = B[block]
            x, y = snap(b['x']), snap(b['y'])
            # the adopted floorplan is authoritative for its own packing (PC row abuts at 20 um): no extra gap there
            if occ.free(x, y, wh[0], wh[1], ignore={block}, gap=(0.0 if (wh[0] <= snap(b['w']) and wh[1] <= snap(b['h'])) else 20.0)):
                occ.add(name, x, y, *wh)
                return x, y, None
            cx, cy = b['x'] + b['w'] / 2, b['y'] + b['h'] / 2
        else:
            cx, cy = prefer
        x, y = occ.near(cx, cy, wh[0], wh[1], ignore={block})
        occ.add(name, x, y, *wh)
        d = round(math.hypot(x + wh[0] / 2 - cx, y + wh[1] / 2 - cy), 1)
        return x, y, d

    def slot(name, cell, src, params, kind, wh, xy, pins, util, entry, extra):
        s = dict(name=name, cell=cell, kind=kind, parent='die', outline=dict(w=wh[0], h=wh[1]),
                 origin=dict(x=xy[0], y=xy[1], orient='R0'), io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2),
                 clock_entry=entry, pg_layer='M5', strap_layer='M6', signal_max_layer='M5', layer_cap='M5',
                 version=1, pins=pins, face_utilisation=util, source=src, params=params, layer_rule='tile')
        s.update(extra)
        slots.append(s)

    # ------------------------------------------------------------------ static COLL homes (4)
    for q in SID:
        i = f'hb_coll_{q}'
        top = inst[i]['master']
        P = ports_of(i)
        blk = f'coll_{q}'
        sy = synth(a.synth, 'coll_q3' if q == 'SW' else 'coll_q2')
        wh, area = need_outline(sy, (B[blk]['w'], B[blk]['h']))
        vm = link_anchor(blk, 'vmb_', 'COLL_VM')
        ep = link_anchor(blk, 'ep_', 'COLL_EP')
        ring = {}
        for e in con['known_actual_edges']:
            for side, other in (('source', 'sink'), ('sink', 'source')):
                if e[side][0] == i and e[other][0].startswith('hb_coll_'):
                    ring[e[side][1]] = 'coll_' + e[other][0][-2:]
        idxl = link_anchor(blk, 'idx_', 'IDX_COLL')
        faces, used = {}, set()
        def put(port, fa):
            if fa is None:
                return
            faces.setdefault(fa[0], []).append((port, P[port][1], fa[1]))
            used.add(port)
        for p in ('vm_rq', 'vm_rr', 'vm_kq'):
            put(p, vm)
        for p, peer in ring.items():
            put(p, link_anchor(blk, peer, 'COLL_RING'))
        for p in P:
            if re.match(r'(tx_pin|rx_pin|phy_up|retry_requested)', p):
                put(p, ep)
        for p in P:
            if re.match(r'(del_|hgi_del_obase|inj_|hgi_inj_addr)', p):
                put(p, idxl or ep)
        taken = set(faces)
        ctl = next((f for f in ('N', 'S', 'E', 'W') if f not in taken), min(faces, key=lambda f: sum(b for _, b, _ in faces[f])))
        for p in P:
            if p not in used:
                faces.setdefault(ctl, []).append((p, P[p][1], None))
        clocks = [p for p in P if p.startswith('clk')]
        wh, pins, util, entry = place_pins(wh, faces, clocks, ctl)
        x, y, d = home(blk, blk, wh)
        if d:
            reloc.append(dict(slot=blk, moved_um=d, reason=f'measured outline {wh} > floorplan {B[blk]["w"]}x{B[blk]["h"]}'))
        slot(blk, top, inst[i]['source'], inst[i]['params'], 'tile', wh, (x, y), pins, util, entry,
             dict(instance=i, synth=sy, need_um2=round(area), control_face=ctl,
                  pins_on_unbound_ports=[p for p in P if p not in used or p in ('inj_d', 'del_flit')]))

    # ------------------------------------------------------------------ SFU engines (4) at the sfu_<q>0 port-group hub
    sy = synth(a.synth, 'sfu')
    for q in SID:
        i = f'hb_sfu_{q}'
        P = ports_of(i)
        blk = f'sfu_{q}0'
        wh, area = need_outline(sy, (B[blk]['w'], B[blk]['h']))
        lg = link_anchor(blk, 'vmb_', 'LG_SFU')
        core = link_anchor(blk, 'sfu_', 'SFU_CORE')
        faces, used = {}, set()
        for p in P:
            if p.startswith('local_'):
                faces.setdefault(lg[0], []).append((p, P[p][1], lg[1])); used.add(p)
        side_face = core[0] if core and core[0] != lg[0] else OPP[lg[0]]
        for p in P:
            if re.match(r'(vi_|side_|ro_|kv_)', p):
                faces.setdefault(side_face, []).append((p, P[p][1], core[1] if core else None)); used.add(p)
        ctl = next(f for f in ('S', 'N', 'W', 'E') if f not in faces)
        for p in P:
            if p not in used:
                faces.setdefault(ctl, []).append((p, P[p][1], None))
        wh, pins, util, entry = place_pins(wh, faces, ['clk'], ctl)
        x, y, d = home(f'hb_sfu_{q}', blk, wh)
        if d:
            reloc.append(dict(slot=f'hb_sfu_{q}', moved_um=d, reason=f'measured SFU engine {wh} > port-group box {B[blk]["w"]}'))
        slot(f'hb_sfu_{q}', inst[i]['master'], inst[i]['source'], inst[i]['params'], 'cluster', wh, (x, y), pins, util, entry,
             dict(instance=i, synth=sy, need_um2=round(area), control_face=ctl, floorplan_block=blk,
                  structural_note=('adopted floorplan has 4 SFU port groups per quadrant (sfu_<q>0..3, LG_SFU 556 b each on '
                                   'different banks); the v15 RTL engine has ONE LG port (lg_<q>_1). Grant = the engine at '
                                   'group 0; groups 1..3 are REQUEST slots until the SFU owner splits the LG face into 4 '
                                   'bank-pair groups (H-ELEM-B)'),
                  pins_on_unbound_ports=[p for p in P if not p.startswith('local_')]))
        for k in (1, 2, 3):
            b = B[f'sfu_{q}{k}']
            occ.add(f'sfu_{q}{k}', b['x'], b['y'], b['w'], b['h'])

    # ------------------------------------------------------------------ DMA back (4): new homes next to the VM bank group
    sy = synth(a.synth, 'dma_back0')
    for q in SID:
        i = f'hb_dbk_{q}'
        P = ports_of(i)
        wh, area = need_outline(sy, (432.0, 302.4))
        vb = B[f'vmb_{q}1']                       # RG1 direct bank n+1 (source comment), floorplan bank 1
        pc = B[f'pc_{q}0']
        for _ in range(3):
            x, y, d = home(i, None, wh, prefer=(vb['x'] + vb['w'] / 2, vb['y'] + vb['h'] / 2))
            box = dict(x=x, y=y, w=wh[0], h=wh[1])
            fvm = face_toward(box, vb['x'] + vb['w'] / 2, vb['y'] + vb['h'] / 2)
            fwb = face_toward(box, pc['x'] + pc['w'] / 2, pc['y'] + pc['h'] / 2)
            if fwb == fvm:
                fwb = next(f for f in ('S', 'N', 'E', 'W') if f != fvm)
            faces, used = {}, set()
            for p in ('rq', 'rr'):
                faces.setdefault(fvm, []).append((p, P[p][1], None)); used.add(p)
            for p in P:
                if p.startswith('wb_') or p in ('wd', 'wa'):
                    faces.setdefault(fwb, []).append((p, P[p][1], None)); used.add(p)
            ctl = next(f for f in ('W', 'E', 'N', 'S') if f not in faces)
            for p in P:
                if p not in used:
                    faces.setdefault(ctl, []).append((p, P[p][1], None))
            wh2, pins, util, entry = place_pins(wh, faces, ['clk'], ctl)
            if wh2 == wh:
                break
            occ.r.pop(); wh = wh2
        slot(i, inst[i]['master'], inst[i]['source'], inst[i]['params'], 'tile', wh, (x, y), pins, util, entry,
             dict(instance=i, synth=sy, need_um2=round(area), control_face=ctl,
                  home_reason=f'no DMA block in T_band2; nearest free spot to VM bank vmb_{q}1 (RG1), {d} um',
                  pins_on_unbound_ports=[p for p in P if p not in ('rq', 'rr')]))

    # ------------------------------------------------------------------ svc bands (PC homes) on the PC row
    svc = json.loads((ROOT / 'physical/hbm_accel_die_views/svc/v15/contract.json').read_text())
    pcv = synth(a.synth, 'svc_pc')
    for rec in svc['instances']:
        i = rec['instance']
        q, k = re.match(r'svc_(\w\w)_s(\d+)', i).groups()
        k = int(k)
        P = ports_of(i)
        blk = f'pc_{q}{k}'
        npc = sum(1 for _ in re.finditer(r'ot_hbm_svc_static_pc', (ROOT / inst[i]['source']).read_text()))
        if blk in B:
            wh = (snap(B[blk]['w']), snap(B[blk]['h']))
            x, y, d = home(i, blk, wh)
        else:
            last = B[f'pc_{q}7']
            wh = (snap(last['w']), snap(last['h']))
            x, y, d = home(i, None, wh, prefer=(last['x'] + last['w'] * 1.5, last['y'] + last['h'] / 2))
            reloc.append(dict(slot=i, moved_um=d, reason='9th service band of the stack has no PC block in T_band2: nearest free spot on the PC row'))
        box = dict(x=x, y=y, w=wh[0], h=wh[1])
        ph = B[f'phy_{q}']
        fphy = face_toward(box, box['x'] + wh[0] / 2, ph['y'] + ph['h'] / 2)
        finner = OPP[fphy]
        faces = {}
        bound_phy = set()
        for e in con['known_actual_edges']:
            for side, other in (('source', 'sink'), ('sink', 'source')):
                if e[side][0] == i and e[other][0].startswith('phy_'):
                    bound_phy.add(e[side][1])
        for p, (dr, bits) in P.items():
            fa = fphy if p in bound_phy else finner
            faces.setdefault(fa, []).append((p, bits, None))
        wh2, pins, util, entry = place_pins(wh, faces, ['clk'], finner)
        # PC child slots: npc x (140.4 x 112.32, the closed hv15_svc_pc outline), one clock entry each (per-PC root)
        kids = []
        cw, chh = 140.4, 112.32
        for c in range(npc):
            cx = snap(10.8 + c * (wh2[0] - 21.6 - cw) / max(1, npc - 1)) if npc > 1 else snap((wh2[0] - cw) / 2)
            cy = snap((wh2[1] - chh) / 2)
            kids.append(dict(name=f'u_pc{c}', cell='ot_hbm_svc_static_pc', outline=dict(w=cw, h=chh),
                             origin=dict(x=cx, y=cy, orient='R0'), clock_entry=dict(pin='clk', face=finner, layer='M5'),
                             own_clock_root=True))
        sub_layouts.setdefault(inst[i]['master'], kids)
        slot(i, inst[i]['master'], inst[i]['source'], {}, 'cluster', wh2, (x, y), pins, util, entry,
             dict(instance=i, floorplan_block=blk if blk in B else None, children=kids, pc_view=pcv,
                  per_pc_root_request=('svcPC native audit FAIL L408.99/C508.02/spread104.7 with one band clock: grant gives each PC '
                                       'its own clock entry (band clk -> clk_pc[%d:0], one CTS root per PC, insertion target <= 300 ps); '
                                       'band RTL generator tools/hbm_svc_v15_contract.py must emit the per-PC clock ports (service owner)' % (npc - 1))))

    # ------------------------------------------------------------------ IDX: scorer clusters (2048 hslices) + glue leaves
    hs_w, hs_h, n_hs = 172.8, 103.68, 512
    scorer_area = n_hs * hs_w * hs_h / 0.80
    sm = synth(a.synth, 'idx_score_meta')
    eg = synth(a.synth, 'idx_engine')
    tl = synth(a.synth, 'idx_tail')
    glue = ((sm or {}).get('std_um2') or 0) + 4 * (((eg or {}).get('std_um2') or 0) + ((tl or {}).get('std_um2') or 0))
    scorer_area += glue / STD_UTIL
    # 20 x 26 hslice array (520 sites >= 512) + glue columns/rows at 0.90: w 3,840 / h ~3,000 fits the 3.4 mm free
    # middle band between the VM hubs (vmh_S* top ~11,270, vmh_N* bottom ~14,710)
    sw = snap(20 * hs_w / 0.90)
    sh = snap(scorer_area / sw)
    sp = ports_src('rtl/hbm_accel/index/ot_hbm_idx_score_static.sv', 'ot_hbm_idx_score_static')
    vmh = B['vmh_SW']
    # middle band, centred on the die, row of 4 scorers (key_lines enter from S/N spine, score leaves toward the selector)
    mid_y = H / 2
    # row order W->E: SW, NW | hc_eng (19,381..20,381, kept) | SE, NE  -> west pair ends at 19,300, east pair starts at 20,450
    he = B['hc_eng']
    xw = he['x'] - 80 - 2 * sw - 60
    xe = he['x'] + he['w'] + 70
    xs = {0: xw, 2: xw + sw + 60, 1: xe, 3: xe + sw + 60}
    for j in range(4):
        nm = f'idx_s{j}'
        x, y, d = home(nm, nm, (sw, sh))  # floorplan box is 500x500: cannot hold 512 hslices -> relocated
        # replace with deterministic centre-band row placement when free
        occ.r.pop()
        tx, ty = snap(xs[j]), snap(mid_y - sh / 2)
        if occ.free(tx, ty, sw, sh, ignore={nm}):
            x, y = tx, ty
        occ.add(nm, x, y, sw, sh)
        faces = {}
        for p, (dr, bits) in sp.items():
            if p in ('key_lines',):
                fa = 'S' if j in (0, 1) else 'N'    # stacks SW/SE feed from the south spine, NW/NE from the north
            elif p == 'score' or p == 'fault':
                fa = 'E' if j < 2 else 'W'          # toward the central selector
            elif p.startswith('ql_') or p in ('beat_v', 'beat_index'):
                fa = 'E' if j < 2 else 'W'
            else:
                fa = 'W' if j < 2 else 'E'
            faces.setdefault(fa, []).append((p, bits, None))
        wh2, pins, util, entry = place_pins((sw, sh), faces, ['clk_ctl'], 'W' if j < 2 else 'E')
        reloc.append(dict(slot=nm, moved_um=round(math.hypot(x - B[nm]['x'], y - B[nm]['y'])),
                          reason=(f'512 CLOSED hslices (ready3 2065d438f, {hs_w}x{hs_h}) = {n_hs * hs_w * hs_h / 1e6:.2f} mm2 per '
                                  f'scorer; T_band2 box 500x500 (0.25 mm2) cannot hold them: scorer cluster {wh2[0]}x{wh2[1]} '
                                  'placed in the empty middle band (ATT freed it)')))
        slot(nm, 'ot_hbm_idx_score_static', 'rtl/hbm_accel/index/ot_hbm_idx_score_static.sv', {}, 'cluster', wh2, (x, y), pins,
             util, entry, dict(instance=f'hb_idx/u_sched/u_parent/scorer[{j}]', stack=SID[j],
                               children=dict(hslice=dict(cell='ot_hbm_idx_hslice_ready_native', count=n_hs, outline=[hs_w, hs_h],
                                                          view='CLOSED ready3-2065d438f exact reuse (Codex IDX 08:30)'),
                                             engine_glue=dict(cell='ot_hbm_idx_engine_static', count=4, synth=eg),
                                             meta=dict(cell='ot_hbm_idx_score_static (local)', synth=sm)),
                               key_lines_long_return=('8,792 b/scorer from stack %s service lines -> scorer: crosses the SM block '
                                                      'through the centre spine (~9-11 mm, relay stations needed, priced by '
                                                      'GLOBAL-FP-H / H-IDX)' % SID[j])))
    # glue leaves next to the scorer row: selector + link + query + vm-operand (near SW VM hub)
    hcx, hcy = he['x'] + he['w'] / 2, he['y'] + he['h']
    leaves = [('idx_sel', 'ot_hbm_idx_selector_static', 'rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv', 'idx_selector', (hcx, hcy + 450)),
              ('idx_link', 'ot_hbm_idx_topk_link_static', 'rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv', 'idx_link', (hcx, hcy + 1100)),
              ('idx_q', 'ot_hbm_idx_query_static', 'rtl/hbm_accel/index/ot_hbm_idx_query_static.sv', 'idx_qbank', (hcx, hcy + 1700)),
              ('idx_op', 'ot_hbm_idx_vm_query_static', 'rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv', 'idx_vmquery',
               (vmh['x'] + vmh['w'] / 2, vmh['y'] + vmh['h'] + 300))]
    for nm, cell, src, sname, pref in leaves:
        sy = synth(a.synth, sname)
        if sy and sname == 'idx_qbank':
            sy = dict(sy, std_um2=4 * sy['std_um2'], note='4 x query bank')
        P = ports_src(src, cell)
        wh, area = need_outline(sy, (B[nm]['w'], B[nm]['h']))
        x, y, d = home(nm, None, wh, prefer=pref)
        box = dict(x=x, y=y, w=wh[0], h=wh[1])
        faces = {}
        # faces: toward scorers row centre for score/ql/beat; toward VM hub for rq/rr; control otherwise
        fsc = face_toward(box, W / 2, mid_y)
        fvm = face_toward(box, vmh['x'] + vmh['w'] / 2, vmh['y'] + vmh['h'] / 2)
        for p, (dr, bits) in P.items():
            if re.match(r'(vm_|rq|rr)', p):
                fa = fvm
            elif p.startswith('clk') or p == 'rst_n':
                fa = OPP[fsc]
            else:
                fa = fsc
            faces.setdefault(fa, []).append((p, bits, None))
        clocks = [p for p in P if p.startswith('clk')]
        wh2, pins, util, entry = place_pins(wh, faces, clocks, OPP[fsc])
        if wh2 != wh:
            occ.r.pop(); occ.add(nm, x, y, *wh2)
        reloc.append(dict(slot=nm, moved_um=round(math.hypot(x - B[nm]['x'], y - B[nm]['y'])), reason='follows the relocated scorer row'))
        slot(nm, cell, src, {}, 'tile', wh2, (x, y), pins, util, entry, dict(synth=sy, need_um2=round(area)))

    # ------------------------------------------------------------------ whole static SU per quadrant: REQUEST slots
    su_req = []
    for q in SID:
        groups = [k for k in B if re.fullmatch(f'su_{q}\\d', k)]
        x0 = min(B[g]['x'] for g in groups); y0 = min(B[g]['y'] for g in groups)
        su_req.append(dict(name=f'hb_su_{q}_top', cell=None, rtl_pending='H-ELEM-B: whole static SU top (VM ports + 512 lanes + '
                           'data store + reducer + RF) as ONE master, 4 bank-pair LG port groups (floorplan condition: SW/SE 4 groups, '
                           'not 5)', port_groups=[dict(name=g, origin=dict(x=snap(B[g]['x']), y=snap(B[g]['y'])),
                                                       outline=dict(w=snap(B[g]['w']), h=snap(B[g]['h'])),
                                                       links=[dict(face=f, cls=p['cls'], peer=p['peer'], bits=p['bits'],
                                                                   offset=round(p['offset_um'], 1)) for f, xx in B[g]['faces'].items()
                                                              for p in xx['pins']]) for g in sorted(groups)],
                           compute_reservation=None))
    # ------------------------------------------------------------------ one pin layout per master cell
    # A physical view has ONE pin plan: slots that share a cell take the plan of the largest instance and a mirror
    # orientation (R0 / MX = N<->S / MY = E<->W / R180) chosen to put the most bits on the faces their own peers want.
    MAPF = dict(R0={}, MX=dict(N='S', S='N'), MY=dict(E='W', W='E'), R180=dict(N='S', S='N', E='W', W='E'),
                R90=dict(N='W', W='S', S='E', E='N'), R270=dict(N='E', E='S', S='W', W='N'),
                MXR90=dict(N='E', E='N', S='W', W='S'), MYR90=dict(N='W', W='N', S='E', E='S'))
    SWAP = {'R90', 'R270', 'MXR90', 'MYR90'}
    groups = {}
    for s in slots:
        groups.setdefault(s['cell'], []).append(s)
    shared = {}
    for cell, ss in groups.items():
        if len(ss) < 2:
            continue
        ref = max(ss, key=lambda s: (s['outline']['w'] * s['outline']['h'], s['name']))
        rf = {pp['name'].split('[')[0]: (pp['face'], int(re.search(r'\[(\d+):', pp['name']).group(1)) + 1 if '[' in pp['name'] else 1)
              for pp in ref['pins']}
        rec = []
        for s in ss:
            want = {pp['name'].split('[')[0]: pp['face'] for pp in s['pins']}
            tot = sum(b for _, b in rf.values())
            best = max(MAPF, key=lambda o: (sum(b for n, (f, b) in rf.items() if MAPF[o].get(f, f) == want.get(n)), o == 'R0'))
            match = sum(b for n, (f, b) in rf.items() if MAPF[best].get(f, f) == want.get(n)) / max(1, tot)
            if s is not ref:
                w0, h0 = s['outline']['w'], s['outline']['h']
                s['own_plan_faces'] = s.pop('face_utilisation')
                s['outline'] = dict(ref['outline']); s['pins'] = [dict(pp) for pp in ref['pins']]
                s['clock_entry'] = dict(ref['clock_entry']) if ref.get('clock_entry') else None
                s['face_utilisation'] = ref['face_utilisation']
                s['origin']['orient'] = best
                x, y = s['origin']['x'], s['origin']['y']
                W2, H2 = (s['outline']['h'], s['outline']['w']) if best in SWAP else (s['outline']['w'], s['outline']['h'])
                s['placed_footprint'] = dict(w=W2, h=H2)
                occ.r = [r for r in occ.r if r[0] != s['name']]
                if not occ.free(x, y, W2, H2, ignore={s.get('floorplan_block') or s['name']}, gap=0.0):
                    nx_, ny_ = occ.near(x + w0 / 2, y + h0 / 2, W2, H2, ignore={s.get('floorplan_block') or s['name']})
                    reloc.append(dict(slot=s['name'], moved_um=round(math.hypot(nx_ - x, ny_ - y), 1),
                                      reason=f'shared master plan of {ref["name"]} ({W2}x{H2}) does not fit the own home'))
                    s['origin']['x'], s['origin']['y'] = nx_, ny_
                occ.add(s['name'], s['origin']['x'], s['origin']['y'], W2, H2)
            s['shared_plan'] = dict(reference=ref['name'], orient=best, own_face_match_bits=round(match, 3))
            rec.append(dict(slot=s['name'], orient=best, face_match=round(match, 3)))
        shared[cell] = rec

    out = dict(schema='opentallas.hier_contract.v1', die='hbm_v15', version=1, owner='H-DIE (Claude)',
               updated=None, clock_period_ps=833.333, floorplan=dict(file=FP, candidate=fp['candidate'],
               adopted='coordinator 2026-10-15 ~09:25 (main 952c5933c)'),
               source_contract=dict(file=CONTRACT, sha256=hashlib.sha256((ROOT / CONTRACT).read_bytes()).hexdigest()),
               rules=dict(step_um_per_bit=STEP, face_cap=FACE_CAP, grid=GRID, std_util=STD_UTIL, macro_halo=HALO,
                          face_layer=FACE_LAYER, homes='adopted block origin if the measured outline fits, else nearest free'),
               slots=[dict(name='die', cell='hbm_v15_top', kind='die', parent=None, outline=dict(w=W, h=H),
                           origin=dict(x=0.0, y=0.0, orient='R0'), clock_entry=dict(pin='pll_ck', face='S', layer='M9'),
                           pg_layer='M9', strap_layer='M9', signal_max_layer='M9', version=1)] + slots,
               sub_layouts=sub_layouts, relocations=reloc, request_slots=su_req, shared_master_plans=shared)
    p = ROOT / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(slots=len(out['slots']), relocations=len(reloc), requests=len(su_req),
                          missing_synth=[s['name'] for s in slots if s.get('synth') is None and s['kind'] != 'die'])))


if __name__ == '__main__':
    main()
