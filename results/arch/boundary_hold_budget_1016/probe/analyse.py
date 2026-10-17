#!/usr/bin/env python3
"""FLOW-HOLD impact analysis: logs (bh_probe) + view libs (libscan.json) + candidates -> impact.json
Per input pin: removable pad fraction r = clamp(slack_after_ff / pad_ff, 0, 1) (pads = HB* cells and BUF* named *hold*);
capture_new = capture_lib - r * pad_tt.  Upper bound 'buf': the same with every BUF/HB stage on the pin->D path
(a registered pin needs none; fanout buffering of a cloned pin flop is the exception, so 'buf' is optimistic).
Outputs likewise with launch (TT O-R)."""
import glob, json, os, re, sys
LOGS, OUT = sys.argv[1], sys.argv[2]
LOGS2 = sys.argv[3] if len(sys.argv) > 3 else None
L = json.load(open('/tmp/claude-1000/flowhold/libscan.json'))
C = json.load(open('/tmp/claude-1000/flowhold/cands.json'))
CAP, LAU, SPR = 190.0, 220.0, 80.0


def parse(f):
    d = dict(i={}, o={}, head={})
    if not os.path.exists(f): return None
    for ln in open(f, errors='replace'):
        p = ln.split()
        if not p: continue
        if p[0] == 'BH_IN' and len(p) >= 6:
            d['i'][p[1]] = dict(slack=float(p[2]), pad=float(p[3]), buf=float(p[4]), dly=float(p[5]), cells=p[6] if len(p) > 6 else '')
        elif p[0] == 'BH_OUT' and len(p) >= 6:
            d['o'][p[1]] = dict(slack=float(p[2]), pad=float(p[3]), buf=float(p[4]), launch=float(p[5]), cells=p[6] if len(p) > 6 else '')
        elif p[0] in ('BH_BEFORE', 'BH_AFTER', 'BH_TT'):
            d['head'][p[0]] = {k: float(v) for k, v in (x.split('=') for x in p[1:])}
        elif p[0] == 'BH_REF':
            d['head']['ref'] = dict(pin=p[1], lmin=float(p[2]), lmax=float(p[3]))
    return d


def frac(s, pad):
    return 0.0 if pad <= 0 else max(0.0, min(1.0, s / pad))


rows = []
for o in C:
    j = o['job']; v = o['view']
    ff = parse(f'{LOGS}/{j}.ff.log'); tt = parse(f'{LOGS}/{j}.tt.log')
    if LOGS2:
        for cor, d in (('ff', ff), ('tt', tt)):
            d2 = parse(f'{LOGS2}/{j}.{cor}.log')
            if d and d2 and d2['o']:
                d['o'] = d2['o']
    lib = L.get(v, {}).get('tt', {})
    rec = dict(cell=o['cell'], view=v, job=j, design=o['audit_design'], used=o['used_in_die'], native=o['native'],
               why=o['native_why'], spread=o['spread_ps'], R=o['R_ps'], cap_lib=o['capture_ps'], launch_lib=o['launch_ps'],
               comb=sum(1 for x in lib.values() if x['comb'] and x['d'] in ('input', 'output')))
    if not ff or 'BH_AFTER' not in ff['head'] or not tt or not tt['i']:
        rec['probe'] = 'missing'; rows.append(rec); continue
    rec['probe'] = 'ok'
    b, a = ff['head']['BH_BEFORE'], ff['head']['BH_AFTER']
    rec['ff_before'] = b; rec['ff_after'] = a
    rec['hold_only_relaxes'] = all(a[k] >= b[k] - 0.01 for k in ('i2r', 'r2o')) and (a['r2r'] == b['r2r'] or abs(a['r2r'] - b['r2r']) < 0.01)
    # inputs
    causes = {}; lcauses = {}
    opad_ff_pre = sum(x['pad'] for x in ff['o'].values())
    cap_new = cap_buf = None; nover = nover_new = 0; pad_ff_tot = pad_rem_ff = 0.0; npad = 0
    worst_pin = None
    for n, x in lib.items():
        if x['d'] != 'input' or x['cap'] is None: continue
        c0 = x['cap']; fi = ff['i'].get(n); ti = tt['i'].get(n)
        cn = cb = c0
        if fi and ti:
            r = frac(fi['slack'], fi['pad']); cn = c0 - r * ti['pad']
            cb = c0 - frac(fi['slack'], fi['buf']) * ti['buf']
            pad_ff_tot += fi['pad']; pad_rem_ff += r * fi['pad']; npad += fi['pad'] > 0
        nover += c0 > CAP; nover_new += cn > CAP
        if c0 > CAP:
            cause = 'pad' if cn <= CAP else None
            if cause is None and ti:
                cells = ti['cells'].split(',') if ti['cells'] else []
                logic = [x for x in cells if not re.match(r'(BUF|HB|INV)', x)]
                if logic: cause = 'logic'
                elif c0 - ti['dly'] > 60: cause = 'clock'      # capture S+R far above the port->D delay: early capture clock
                else: cause = 'wire_buffer'
            causes[cause or 'unprobed'] = causes.get(cause or 'unprobed', 0) + 1
        if cap_new is None or cn > cap_new: cap_new, worst_pin = cn, n
        cap_buf = cb if cap_buf is None else max(cap_buf, cb)
    # die-side demand per receiving pin (RULE.md D3): need_new = today's FF need (H-R) + the pad delay removed;
    # demand(D) = max(0, D + U + need_new - C - w) with U = C = 25, w = 0 -> max(0, D + need_new)
    flib = L.get(v, {}).get('ff', {})
    dem = {0: [], 40: [], 80: []}; need_new_all = []
    for n, x in flib.items():
        if x['d'] != 'input' or x['hold'] is None: continue
        fi = ff['i'].get(n)
        rem = frac(fi['slack'], fi['pad']) * fi['pad'] if fi else 0.0
        nn = x['hold'] + rem; need_new_all.append(nn)
        for D in dem: dem[D].append(max(0.0, D + nn))
    if need_new_all:
        rec['die_need_new_ps'] = dict(max=round(max(need_new_all), 1), median=round(sorted(need_new_all)[len(need_new_all) // 2], 1))
        rec['die_demand'] = {str(D): dict(pins=len(v_), pins_pos=sum(1 for z in v_ if z > 0), mean=round(sum(v_) / len(v_), 1),
                                          max=round(max(v_), 1)) for D, v_ in dem.items()}
        rec['tile_pad_now_ff_per_pin'] = round((pad_ff_tot + opad_ff_pre) / max(1, len(need_new_all)), 1)
    lib_est = [0]
    lau_new = lau_buf = None; lover_new = 0; opad_ff = opad_rem = 0.0
    for n, x in lib.items():
        if x['d'] != 'output' or x['lo'] is None: continue
        l0 = x['lo']; fo = ff['o'].get(n); to = tt['o'].get(n)
        ln = lb = l0
        if not (fo and to):
            # lib-based estimate (probe path missing): surplus output padding = FF launch-min beyond clk->Q+INV (40 ps)
            lmf = flib.get(n, {}).get('lmin')
            if lmf is not None:
                ln = lb = l0 - 1.4 * max(0.0, lmf - 40.0); lib_est[0] += 1
        if fo and to:
            r = frac(fo['slack'], fo['pad']); ln = l0 - r * to['pad']; lb = l0 - frac(fo['slack'], fo['buf']) * to['buf']
            opad_ff += fo['pad']; opad_rem += r * fo['pad']
        lover_new += ln > LAU
        if l0 > LAU:
            cause = 'pad' if ln <= LAU else None
            if cause is None and not to: cause = 'clock_or_wire(lib)'
            if cause is None and to:
                cells = to['cells'].split(',') if to['cells'] else []
                logic = [x for x in cells if not re.match(r'(BUF|HB|INV)', x)]
                cause = 'logic' if logic else ('wire_buffer' if to['buf'] > 60 else 'clock')
            lcauses[cause or 'unprobed'] = lcauses.get(cause or 'unprobed', 0) + 1
        lau_new = ln if lau_new is None else max(lau_new, ln)
        lau_buf = lb if lau_buf is None else max(lau_buf, lb)
    # sender guarantee today: min FF launch at outputs (rel. L_min) and the pad-free outputs' launch (= clk->Q + wire)
    lm = [x['launch'] for x in ff['o'].values()]
    lm0 = [x['launch'] for x in ff['o'].values() if x['buf'] <= 0.0]
    rec.update(launch_lib_estimated=lib_est[0], cap_causes=causes, launch_causes=lcauses, cap_new=cap_new and round(cap_new, 1), cap_buf=cap_buf and round(cap_buf, 1), cap_worst_pin=worst_pin,
               cap_over=nover, cap_over_new=nover_new, launch_new=lau_new and round(lau_new, 1),
               launch_buf=lau_buf and round(lau_buf, 1), launch_over_new=lover_new,
               in_pad_ff_ps=round(pad_ff_tot), in_pad_removable_ff_ps=round(pad_rem_ff), in_padded_pins=npad, inputs=len(ff['i']),
               out_pad_ff_ps=round(opad_ff), out_pad_removable_ff_ps=round(opad_rem), outputs=len(ff['o']),
               ff_launch_min=round(min(lm), 1) if lm else None, ff_launch_min_unpadded=round(min(lm0), 1) if lm0 else None)
    # classification of a native FAIL
    if o['native'] == 'FAIL':
        sp = (o['spread_ps'] or 0) > SPR
        cap_ok = cap_new is None or cap_new <= CAP
        lau_ok = lau_new is None or lau_new <= LAU
        allc = {**{'in_' + k: v for k, v in causes.items()}, **{'out_' + k: v for k, v in lcauses.items()}}
        if not o.get('R_ps') and 'insertion' in (o['native_why'] or ''): cls = 'D_no_insertion_json'
        elif rec['comb']: cls = 'C_combinational_pins'
        elif sp: cls = 'B_insertion_spread'
        elif cap_ok and lau_ok: cls = 'A_padding_only'
        elif any(k.endswith('clock') for k in allc): cls = 'B_insertion_spread'
        elif any(k.endswith('logic') for k in allc): cls = 'B_logic_at_pin'
        else: cls = 'B_pinflop_wire'
        rec['class'] = cls
    rows.append(rec)
json.dump(rows, open(OUT, 'w'), indent=1)
for r in rows:
    if r['probe'] != 'ok': print('MISSING', r['view']); continue
    print(f"{r['native']:4} {r.get('class',''):30} {r['cell'][:28]:28} cap {r['cap_lib']}->{r['cap_new']} (buf {r['cap_buf']}) "
          f"launch {r['launch_lib']}->{r['launch_new']} spr {r['spread']} relax={r['hold_only_relaxes']} "
          f"{r['cap_causes']} {r['launch_causes']} inpad {r['in_pad_removable_ff_ps']}/{r['in_pad_ff_ps']} outpad {r['out_pad_removable_ff_ps']}/{r['out_pad_ff_ps']} lmin {r['ff_launch_min']}/{r['ff_launch_min_unpadded']}")
