#!/usr/bin/env python3
"""Q-CLUSTER5: per-root child-FLOP spread = CTS pin arrival + child internal insertion (stand-in lib clock_tree_path)."""
import json, re, sys, glob, collections
# usage: flop_spread.py CK_JSON STANDIN_KIT_DIR   (STANDIN_KIT_DIR = physical/ref_tile/qfd_c_b16_dv_diag)
ck = json.load(open(sys.argv[1])); kit = sys.argv[2]
def libpins(path):
    t = open(path).read(); out = {}
    for m in re.finditer(r'pin\("?(\w+)"?\)\s*\{(.*?)\n    \}', t, re.S):
        b = m.group(2)
        mn = re.search(r'min_clock_tree_path.*?values\("([\d.]+)"', b, re.S)
        mx = re.search(r'max_clock_tree_path.*?values\("([\d.]+)"', b, re.S)
        if mx: out[m.group(1)] = (float(mn.group(1)), float(mx.group(1)))
    return out
lat = {}
for d in glob.glob(kit + '/*_standin/*/'):
    mname = d.rstrip('/').split('/')[-1]
    for c in ('tt', 'ff'):
        f = glob.glob(d + f'*_{c}.lib')
        if f: lat[(mname, c)] = libpins(f[0])
a0_inst = set()
for r, v in ck['clock_measurements'].items():
    for p in v['tt']['macros']['pins']:
        i, pn = p['pin'].rsplit('/', 1)
        if pn != 'ck': a0_inst.add(i)
place = open(kit.replace('qfd_c_b16_dv_diag', sys.argv[3]) + '/place.tcl').read() if len(sys.argv) > 3 else ''
def master(inst):
    m = re.search(r'\{?' + re.escape(inst) + r'\}?\s+(\S+)', place)
    return None
res = {}
for r, v in ck['clock_measurements'].items():
    res[r] = {}
    for c in ('tt', 'ff'):
        rows = []
        for p in v[c]['macros']['pins']:
            i, pn = p['pin'].rsplit('/', 1)
            if i in a0_inst:
                ms = 'qfd_tile_nl_rp2_romleaf_rr' if pn in lat[('qfd_tile_nl_rp2_romleaf_rr', c)] and pn not in lat[('qfd_tile_nk_rp2_romleaf_rr', c)] else 'qfd_tile_nk_rp2_romleaf_rr'
                lo, hi = lat[(ms, c)].get(pn, lat[('qfd_tile_nl_rp2_romleaf_rr', c)].get(pn, (None, None)))
                kind = 'A0'
            else:
                lo, hi = lat[('qfd_c_stn516', c)]['ck']; kind = 'stn'
            rows.append((p['arr'], p['arr'] + lo, p['arr'] + hi, kind, p['pin']))
        regs = v[c]['all'] if 'all' in v[c] else {}
        pa = [x[0] for x in rows]; fl = [x[1] for x in rows] + [x[2] for x in rows]
        a0 = [x for x in rows if x[3] == 'A0']; st = [x for x in rows if x[3] == 'stn']
        res[r][c] = dict(n=len(rows), pin_min=min(pa), pin_max=max(pa), pin_spread=round(max(pa)-min(pa),1),
            flop_min=round(min(fl),1), flop_max=round(max(fl),1), flop_spread=round(max(fl)-min(fl),1),
            a0_pin=[min(x[0] for x in a0), max(x[0] for x in a0)] if a0 else None,
            stn_pin=[min(x[0] for x in st), max(x[0] for x in st)] if st else None,
            soft_regs=[v[c]['boundary'].get('min'), v[c]['boundary'].get('max')] if v[c].get('boundary') else None,
            latest=max(rows)[4], earliest=min(rows)[4])
json.dump(res, sys.stdout, indent=1)
