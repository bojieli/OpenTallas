#!/usr/bin/env python3
"""PATH-S81-PD6: replay the clock-landing storage-band search (clock_landing_plan._storage_band, unchanged) for one
composed type with its hard-core set rigidly shifted by (dx, dy); report band failures and FT-site/outline conflicts.
usage: sim_shift.py WT COMPOSED SIDE OUT_JSON LANDED_JSON  (reads shifts from stdin JSON {type: [[dx,dy],...]} )"""
import json, sys, copy
wt, comp, sidep, outp = sys.argv[1:5]
sys.path.insert(0, wt + '/tools/die_plan')
import clock_landing_plan as CLP, reset_tree as RT
raw = json.load(open(comp)); col = json.load(open(sidep))['collector']
req = json.load(sys.stdin); res = {}
WID = {}
_pp = {p['id']: p for p in raw['ports']}; _pt = {p['name']: p['type'] for p in raw['partitions']}
for r in json.load(open(sys.argv[5]))['ports']:
    WID[(_pt[r['dst']], _pp[r['port']]['dst']['bus'])] = int(r['width'])
def ovl(a, b): return min(a[2], b[2]) > max(a[0], b[0]) + 1e-6 and min(a[3], b[3]) > max(a[1], b[1]) + 1e-6
for tn, shifts in req.items():
    base = raw['partition_types'][tn]; info = col['types'][tn]
    for dx, dy in shifts:
        t = copy.deepcopy(base); t['_cland_geom'] = info.get('bus_geometry', {})
        w, h = t['outline_um']
        for c in t.get('hard_cores', []):
            c['origin_um'] = [round(c['origin_um'][0] + dx, 6), round(c['origin_um'][1] + dy, 6)]
        blk = RT.blockages(t)
        out_of = sum(1 for b in blk if b[0] < 0 or b[1] < 0 or b[2] > w or b[3] > h)
        ft = []
        for slot in t.get('ft_slots', []):
            cell = slot.get('bit_site_cell_um', [1.404, .27])
            for st in slot.get('bit_sites_um', []):
                if st: ft.append((slot['name'], [min(p[0] for p in st)-cell[0]/2, min(p[1] for p in st)-cell[1]/2, max(p[0] for p in st)+cell[0]/2, max(p[1] for p in st)+cell[1]/2]))
            for x, y in slot.get('regs_um', []) if not slot.get('bit_sites_um') else []:
                ft.append((slot['name'], [x-.5, y-.5, x+.5, y+.5]))
        blk0 = RT.blockages(t, 0.0)
        ftc = sorted({n for n, r in ft if any(ovl(r, b) for b in blk0)})
        used = []; fails = []; placed = 0
        for c in info.get('children', []):
            if c.get('seam'): t.setdefault('buses', []).append(CLP._scalar(t, f"cland_dn_ready_{c['index']}", 'in', c['xy_um'], 'ctl', shift=2.16*2))
        order = [k for k in sorted(info['bands']) if not k.startswith('monitor_')] + sorted((k for k in info['bands'] if k.startswith('monitor_')), key=lambda k: int(k.split('_')[1]))
        for k in order:
            bd = info['bands'][k]; mon = k.startswith('monitor_')
            bus = k if not mon else 'cland_dn_ready_' + k.split('_')[1]
            wd = 2 if mon else (bd.get('width') or WID.get((tn, k)))
            try:
                b = CLP._storage_band(t, bus, int(wd), used, has_epoch=not mon); used.append(b['rect_um']); placed += 1
            except ValueError as e:
                fails.append(k)
        res.setdefault(tn, []).append(dict(dx=dx, dy=dy, placed=placed, fails=fails, cores_outside=out_of, ft_slots_hit=ftc, ft_hit=len(ftc)))
        print(tn, dx, dy, 'placed', placed, 'fails', fails, 'outside', out_of, 'ft_hit', len(ftc), ftc[:6], flush=True)
json.dump(res, open(outp, 'w'), indent=1)
