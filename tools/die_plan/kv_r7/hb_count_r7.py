"""CLOCK-KV-R6 data hold-buffer count from the REAL endpoint list (12.4a a1): every abutted plan port bit
(DC.seam_pairs: nearest src-part tap / dst-part tap under the pin register = the bit's launch/capture clock), zero-logic
reg->reg (structural worst case; real logic only lowers the count), flat derates as die_sta_related (FF hold, TT setup),
CPPR credit at the last common tree node.  HB4 per cell: 44.6 ps FF early / 83.0 ps TT late (HOLD-REPAIR estimate basis).
usage: hb_count_r7.py TOOLDIR PLAN PREDDIR [AOCVDIR TABLE [TT=u,FF=u [TT=solve.json,FF=solve.json ROUTED_BUILD_DIR]]]  (R7: signed-mesh uncertainty on node-m pairs)  (with AOCVDIR: CLK-AOCV table pessimism per pair, 12.4a b1 v5.0)"""
import sys, json, math, collections
sys.path.insert(0, sys.argv[1]); import die_clock as DC, schema as S
P = S.Plan(S.load(sys.argv[2])); d = sys.argv[3]
M = json.load(open(d + '/mesh.json'))
T = {c: json.load(open(f'{d}/tap_arrivals_{c}.json')) for c in ('TT', 'FF')}
R = {c: json.load(open(f'{d}/rel_{c}/regchar/{c}.json')) for c in ('TT', 'FF')}
tb = collections.defaultdict(list)
for t in M['taps']: tb[t['part']].append(dict(port=t['port'], part=t['part'], xy=t['xy']))
bits = DC.seam_pairs(P, tb)
band = {t['port'] for t in M['taps'] if t.get('mesh_in')}
def arr(c):
    return {r['port']: r for r in T[c]['taps']}, T[c]['cppr_node_range_ps']
A = {c: arr(c) for c in ('TT', 'FF')}
OCV = {}
if len(sys.argv) > 5:
    sys.path.insert(0, sys.argv[4]); import importlib; DSR = importlib.import_module('die_sta_related_r7')
    if len(sys.argv) > 6: DSR.MESH_UNC.update({k: float(v) for k, v in (x.split('=') for x in sys.argv[6].split(','))})
    if len(sys.argv) > 8: DSR.load_mesh_pairs(sys.argv[7], sys.argv[8])
    for c in ('TT', 'FF'):
        tp = {r['port']: r for r in T[c]['taps']}
        OCV[c] = DSR.clock_ocv_fn('table', 'shared', dict(T[c], corner=c), tp, 250.0, sys.argv[5])
ocv = lambda c, a, b, k: OCV[c](a, b, k) if c in OCV else 0.0
def cred(c, a, b):
    t, rng = A[c]; la, ea, lb, eb = t[a]['late_ps'], t[a]['early_ps'], t[b]['late_ps'], t[b]['early_ps']
    return min(max(0., rng.get('h', 0.)), max(0., la - ea), max(0., lb - eb))
HB_FF, HB_TT, PER, US, UH = 44.6, 83.0, 833.333, 60.0, 25.0
tot = collections.Counter(); cells = 0; nbits = 0; worst_setup_after = None; fail_after = 0; hist = collections.Counter()
for (a, b, pid), n in bits.items():
    tf, _ = A['FF']; tt, _ = A['TT']
    hold = (tf[a]['early_ps'] + R['FF']['clkq_min_nowire_ps']) - (tf[b]['late_ps'] + R['FF']['hold_ps']) - UH + cred('FF', a, b) - ocv('FF', a, b, 'hold')
    setup = PER - US - (tt[a]['late_ps'] + R['TT']['clkq_max_wire_ps']) + (tt[b]['early_ps'] - R['TT']['setup_ps']) + cred('TT', a, b) - ocv('TT', a, b, 'setup')
    k = max(0, math.ceil(-hold / HB_FF)) if hold < 0 else 0
    cls = 'band' if (a in band or b in band) else 'array'
    nbits += n; tot[cls + '_bits'] += n
    if k:
        tot[cls + '_bits_fail'] += n; tot[cls + '_cells'] += k * n; cells += k * n; hist[k] += n
    s2 = setup - k * HB_TT
    worst_setup_after = s2 if worst_setup_after is None else min(worst_setup_after, s2)
    fail_after += n if s2 < 0 else 0
out = dict(mesh_unc=getattr(DSR, 'MESH_UNC', None) if OCV else None, mesh_unc_pairs=sys.argv[7] if len(sys.argv) > 8 else None, endpoints_bits=nbits, hb4_cells=cells, hb4_area_um2=round(cells * 0.1021, 1), by_class=dict(tot),
           cells_per_bit_hist=dict(sorted(hist.items())), tt_setup_worst_after_insertion_ps=round(worst_setup_after, 2),
           tt_setup_fail_bits_after=fail_after, basis=__doc__.split('\n')[0], status='UNCHECKED')
print(json.dumps(out)); out['clock_ocv'] = 'table ' + sys.argv[5] if OCV else 'none'
import os; json.dump(out, open(os.environ.get('HB_OUT') or (d + ('/hb_count_aocv.json' if OCV else '/hb_count.json')), 'w'), indent=1)
