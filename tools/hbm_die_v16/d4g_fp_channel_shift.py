#!/usr/bin/env python3
"""L2H-GEN2D-FP 10-19 (LEAD3-HBM decision 22:57): widen the sfucore <-> hb_dbk/hc channel of every quadrant by one
43.2 um macro-lattice step so the stream reset forest has stage homes beside the 624-bit lane crossroads.

  NW/SW: hb_dbk_<q> and hc_<q> move EAST by 43.2 um (sfucore_<q> right edge -> hb_dbk/hc gap 55 -> 98 um).
  NE/SE: hc_<q> moves WEST by 43.2 um (hc_<q> right edge -> sfucore_<q> gap 100 -> 143 um).  hb_dbk_NE/SE have no grant
         slot in this die (die_case places them from prior homes far from the channel), so nothing else moves there.
  calendar_SW moves EAST by 43.2 um with hc_SW (hc_SW's new east edge would overlap it by 19 um).

Only slot ORIGINS change; outlines, orientations, pins and every other grant field stay.  The script refuses a shift that
creates a new slot-outline overlap or leaves the die.  The d4g plan blocks of the same blocks (hc_<q>, dbk_NW/SW) move by
the same dx so plan regions and slots stay aligned.
Cell labels: 6 GEN2c slots carry the pre-wrapper cell names (calendar_* hfd_hgi_vm_calendar, fs_SW/NW ot_hbm_fault_leaf) while the
GEN2c contract binds the selected wrappers (_f20, _n8_s0); die_case_v16 (grant_slot_bind) refuses explicit-instance slots whose
cell differs from the contract master, so CELL_SYNC renames exactly those labels (as 9d5a2c350 did for GEN2e; no geometry change).
Usage: d4g_fp_channel_shift.py in_grants.json out_grants.json [in_plan.json out_plan.json]
"""
import json, sys

STEP = 43.2
PLAN_SHIFT = {'dbk_NW': STEP, 'hc_NW': STEP, 'dbk_SW': STEP, 'hc_SW': STEP, 'hc_NE': -STEP, 'hc_SE': -STEP}
CELL_SYNC = {f'calendar_{q}': ('hfd_hgi_vm_calendar', 'hfd_hgi_vm_calendar_f20') for q in ('SW', 'SE', 'NW', 'NE')}
CELL_SYNC.update({f'fs_{q}': ('ot_hbm_fault_leaf', 'ot_hbm_fault_leaf_n8_s0') for q in ('SW', 'NW')})
SHIFT = {'hb_dbk_NW': STEP, 'hc_NW': STEP, 'hb_dbk_SW': STEP, 'hc_SW': STEP, 'calendar_SW': STEP,
         'hc_NE': -STEP, 'hc_SE': -STEP}


def rect(s):
    o, w = s['origin'], s['outline']
    return (o['x'], o['y'], o['x'] + w['w'], o['y'] + w['h'])


def overlaps(slots):
    real = [s for s in slots if s['origin']['x'] >= 100 or s['origin']['y'] >= 100]   # origin slots = placeholders
    out = set()
    for i, a in enumerate(real):
        ra = rect(a)
        for b in real[i + 1:]:
            rb = rect(b)
            if ra[0] < rb[2] - 1e-6 and rb[0] < ra[2] - 1e-6 and ra[1] < rb[3] - 1e-6 and rb[1] < ra[3] - 1e-6:
                out.add(tuple(sorted((a['name'], b['name']))))
    return out


def main():
    g = json.load(open(sys.argv[1]))
    slots = g['slots']
    before = overlaps(slots)
    by = {s['name']: s for s in slots}
    missing = sorted(set(SHIFT) - set(by))
    if missing:
        raise SystemExit(f'slots missing: {missing}')
    W = g.get('die', {}).get('w_um') if isinstance(g.get('die'), dict) else None
    moved = {}
    for n, dx in SHIFT.items():
        s = by[n]; x0 = s['origin']['x']
        s['origin']['x'] = round(x0 + dx, 3)
        s['fp_channel_shift_1019'] = dict(dx_um=dx, from_x=x0, to_x=s['origin']['x'],
                                          why='L2H-GEN2D-FP: widen sfucore<->hb_dbk/hc channel by one 43.2 um lattice step for reset forest stage homes')
        moved[n] = [x0, s['origin']['x']]
        if s['origin']['x'] < 0 or (W and s['origin']['x'] + s['outline']['w'] > W):
            raise SystemExit(f'{n} leaves the die')
    for n, (old, new) in CELL_SYNC.items():
        if by[n].get('cell') != old:
            raise SystemExit(f'{n}: cell {by[n].get("cell")} != expected {old}')
        by[n]['cell'] = new; by[n]['fp_cell_sync_1019'] = f'{old} -> {new} (contract master)'
    after = overlaps(slots)
    new = sorted(after - before)
    if new:
        raise SystemExit(f'new slot overlaps: {new}')
    g.setdefault('fp_channel_shift_1019', {})
    g['fp_channel_shift_1019'] = dict(step_um=STEP, moved=moved, overlaps_before=len(before), overlaps_after=len(after),
                                      new_overlaps=new, decision='LEAD3-HBM 10-19 22:57')
    json.dump(g, open(sys.argv[2], 'w'), indent=1)
    if len(sys.argv) > 4:
        p = json.load(open(sys.argv[3])); pm = {}
        for n, dx in PLAN_SHIFT.items():
            b = p[n]; x0 = b['x']; b['x'] = round(x0 + dx, 3); pm[n] = [x0, b['x']]
        p['fp_channel_shift_1019'] = dict(step_um=STEP, moved=pm, decision='LEAD3-HBM 10-19 22:57')
        json.dump(p, open(sys.argv[4], 'w'), indent=1)
        print('FP_PLAN_SHIFT', json.dumps(pm))
    print('FP_SHIFT', json.dumps(dict(moved=moved, overlaps_before=len(before), overlaps_after=len(after), new=new)))


if __name__ == '__main__':
    main()
