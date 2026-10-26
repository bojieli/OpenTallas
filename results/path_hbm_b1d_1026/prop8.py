import json, math, re, glob, os, sys
S = '/srv/opentallas-scratch2/claude/hbm-core-lat-1026/place_b1'
L, M, FILL, PP = 8.64, 4.32, 0.6, 0.192   # lattice, halo/margin, target std fill of free area, min pin pitch per pin (4-track)
out = []
for K in sorted(glob.glob(S + '/kits/*-_b1pl')):
    cfg = open(K + '/config.mk').read()
    die = [float(v) for v in re.search(r'DIE_AREA = ([\d. ]+)', cfg).group(1).split()][2:]
    log = glob.glob(K + '/run/logs/asap7/*/base/3_4_place_resized.log')
    da = float(re.findall(r'Design area (\d+) um\^2', open(log[0]).read())[-1]) if log else None
    pins = sum(1 for l in open(K + '/io.tcl') if l.startswith('place_pin'))
    macs = []
    for lef in glob.glob(K + '/macros/*.lef'):
        t = open(lef).read()
        nm = re.search(r'^MACRO (\S+)', t, re.M).group(1); w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', t).groups())
        st = open(glob.glob(K + '/run/reports/asap7/*/base/synth_stat.txt')[0]).read()
        cnt = [int(m.group(1)) for m in re.finditer(r'^\s+(\d+)\s.*\s' + re.escape(nm) + r'\s*$', st, re.M)]
        n = max(cnt) if cnt else 0
        macs.append((nm, n, w, h))
    mac_area = sum(n * w * h for _, n, w, h in macs)
    mac_halo = sum(n * (w + M) * (h + M) for _, n, w, h in macs)
    std = da - mac_area
    need = std / FILL + mac_halo                       # core area needed
    ar = die[1] / die[0]
    # smallest lattice outline with the current aspect ratio meeting area, perimeter (pins) and largest macro
    s = 1.0
    while True:
        w = math.ceil(die[0] * s / L) * L; h = math.ceil(die[1] * s / L) * L
        ok_area = (w - 2 * M) * (h - 2 * M) >= need
        ok_pin = 2 * (w + h) >= pins * PP
        ok_mac = all(w >= mw + 4 * M and h >= mh + 4 * M for _, n, mw, mh in macs if n)
        if not (ok_area and ok_pin and ok_mac) or s < 0.05:
            break
        best = (round(w, 3), round(h, 3)); s -= 0.01
    best = best if 'best' in dir() and best else (die[0], die[1])
    lim = 'pin-limited' if 2 * (best[0] + best[1]) < pins * PP * 1.05 else 'area-limited'
    fr = lambda W, H: round(std / ((W - 2 * M) * (H - 2 * M) - mac_halo), 3)
    out.append(dict(kit=os.path.basename(K), outline_now_um=die, outline_proposed_um=list(best), std_area_um2=round(std),
                    macros=[dict(name=a, n=b, um=[c, d]) for a, b, c, d in macs], pins=pins,
                    est_fill_of_free_now=fr(*die), est_fill_of_free_proposed=fr(*best),
                    area_change=round(best[0] * best[1] / (die[0] * die[1]) - 1, 3), limit=lim))
    del best
json.dump(dict(_note='Outline-from-content proposals for the 8 place_b1 types (GEOM-REVIEW-3). std area = placed design area (3_4 resized) - macro area; '
               'target std fill 0.6 of free core (core minus macro+4.32 halo), sides on 8.64 lattice, current aspect ratio kept, '
               'perimeter >= pins x 0.192 um. UNCHECKED (12.9f), not applied; b1e sizes these before any CTS.', proposals=out),
          open(S + '/outline_proposals_place8.json', 'w'), indent=1)
for p in out: print(p['kit'][:40], p['outline_now_um'], '->', p['outline_proposed_um'], p['est_fill_of_free_now'], '->', p['est_fill_of_free_proposed'], p['pins'], [ (m['n'],m['um']) for m in p['macros']], p['limit'], p['area_change'])
