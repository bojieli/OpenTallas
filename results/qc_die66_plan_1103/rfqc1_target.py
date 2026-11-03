#!/usr/bin/env python3
"""DIE-QC-66/PLAN RF-QC-1 shape TARGET table (advisory) (plan arithmetic, UNCHECKED until a build measures it).

Per partition type of the QC plan: soft std cells (measured placed std_cells where an AUTO-GEOM dump exists, else the
cells evidence / plan estimate MINUS the planned/signed hard-core cells it contains), std area at the measured
um2/cell, hard-macro area, face pins, and the RE-FORM slot: area = macros + std/fill (fill 0.40, glue 0.30),
side >= pins / (face_pins_per_um x 2 faces) so the face holds the pins, aspect <= 3, split n = ceil(soft / 150k).
usage: rfqc1_estimate.py PLAN CELLS_EVIDENCE PLAN_NOTES GEOM_METRICS CLS OUT.json OUT.tsv
"""
import json, math, sys, collections
plan, ev, notes, gm, cls, oj, ot = sys.argv[1:8]
P = json.load(open(plan)); T = P['partition_types']
EV = json.load(open(ev))['cells_per_type']; N = json.load(open(notes)); G = json.load(open(gm)); C = json.load(open(cls))
CORE_CELLS = {'qfd_tile_nk_a0c': 187991, 'qfd_tile_nl_a0c': 187991, 'qfd_dv_s8x_vmr': 82688, 'qfd_dv_s8_crh_rp1': 82688,
              'qfd_dv_s8x_prog': 105945, 'qfd_dv_s8x_btab': 105945, 'qfd_dv_s5_su8_rst3': 25840, 'qfd_dv_s5_red2_leaf': 110897,
              'qfd_coll_static_face': 116000}
for k in range(8): CORE_CELLS[f'qfd_qc_su_lane_w_l{k}'] = 103360
UM2 = 0.155            # measured median um2/std cell (7 placed QC kits: 0.137-0.168)
CAP = 150000; PPU = P['budgets']['face_pins_per_um']
inst = collections.Counter(p['type'] for p in P['partitions'])
rows = []
for tn, t in sorted(T.items()):
    W, H = t['outline_um']
    hc = t.get('hard_cores', [])
    cores = [h for h in hc if h['module'] in CORE_CELLS]
    srams = [h for h in hc if h['module'] not in CORE_CELLS]
    core_cells = sum(CORE_CELLS[h['module']] for h in cores)
    if tn in G:
        soft, basis = G[tn]['cells'], 'placed'
    else:
        tot = t.get('cells') or (EV.get(tn) or {}).get('cells')
        soft, basis = (None, 'none') if tot is None else (max(0, tot - core_cells), 'est')
    mac = sum(h['outline_um'][0] * h['outline_um'][1] for h in hc)
    mac_sram = sum(h['outline_um'][0] * h['outline_um'][1] for h in srams)
    pins = sum(b['width'] for b in t.get('buses', []))
    face = collections.Counter()
    for b in t.get('buses', []): face[b.get('face', '?')] += b['width']
    glue = tn == 'glue' or tn.startswith('coll_n')
    fill = 0.30 if glue else 0.40
    std = (soft or 0) * UM2
    n = max(1, math.ceil((soft or 0) / CAP))
    cls_ = C.get(tn, ['?'])[0]
    # RE-FORM slot per split block (macros on the edge stay with their block; cores keep their signed outline)
    slot_area = mac + std / fill
    side_pins = pins / (PPU * 2) if pins else 0     # pins spread over 2 opposite faces at the face budget
    rows.append(dict(type=tn, cls=cls_, inst=inst[tn], outline=[W, H], area=round(W * H), aspect=round(max(W, H) / min(W, H), 2),
                     soft_cells=soft, basis=basis, core_cells=core_cells, n_cores=len(cores), n_sram=len(srams),
                     macro_area=round(mac), std_area=round(std), fill_now=round(std / max(1, W * H - mac), 4),
                     slot_area=round(slot_area), shrink=round(slot_area / (W * H), 3), split_n=n,
                     pins=pins, faces=dict(face), side_min_pins=round(side_pins, 1)))
json.dump(rows, open(oj, 'w'), indent=0)
with open(ot, 'w') as f:
    keys = ['type', 'cls', 'inst', 'outline', 'aspect', 'soft_cells', 'basis', 'core_cells', 'n_cores', 'n_sram', 'macro_area', 'std_area', 'fill_now', 'slot_area', 'shrink', 'split_n', 'pins', 'side_min_pins']
    f.write('\t'.join(keys) + '\n')
    for r in rows: f.write('\t'.join(str(r[k]) for k in keys) + '\n')
c = collections.Counter(); tot = collections.Counter()
for r in rows:
    big = (r['soft_cells'] or 0) > CAP
    c[(r['cls'], 'big' if big else 'ok')] += 1
    tot['area_now'] += r['area'] * r['inst']; tot['slot'] += r['slot_area'] * r['inst']
print(sorted(c.items())); print({k: round(v / 1e6, 2) for k, v in tot.items()}, 'mm2 (x instances)')
print('types >150k soft:', [ (r['type'], r['soft_cells'], r['basis']) for r in rows if (r['soft_cells'] or 0) > CAP])
print('types no cells:', [r['type'] for r in rows if r['soft_cells'] is None])
