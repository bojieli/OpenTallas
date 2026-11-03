"""XCHECK-1 area report: slots + channels + repeater bays vs die outline (report only, never a gate).
usage: python3 -I xchk_area.py DIE_PLAN.json [REFORM.json]
slot   = partition outline (type outline_um, orient-aware) excluding station/relay/bay types
bay    = partitions whose type name looks like a station / relay / repeater bay / shim / turn
chan   = die outline - slots - bays (streets / M6-M7 channels / free)
cores  = hard_core slots inside types x instances (subset of slot area)
REFORM = optional list rows {module,n_inst,old,new,fits_parent}: delta core-slot area and non-fitting rows."""
import json, re, sys, collections

BAY = re.compile(r'(station|_st[a-z_]*\b|^st_|relay|bay|shim|turn|_stm|_fw|_fe|rep)', re.I)

p = json.load(open(sys.argv[1]))
W, H = p['die']['outline_um']
A = W * H
T = p['partition_types']
if isinstance(T, list):
    T = {t.get('name') or t.get('module'): t for t in T}
slot = bay = 0.0
cnt = collections.Counter()
core = 0.0
bb = [1e18, 1e18, -1e18, -1e18]
for q in p['partitions']:
    t = T.get(q['type'], {})
    o = t.get('outline_um') or [0, 0]
    if 'rect_um' in q:
        x0, y0, x1, y1 = q['rect_um']
    else:
        w, h = o
        if q.get('orient', 'R0') in ('R90', 'R270', 'MXR90', 'MYR90'):
            w, h = h, w
        x0, y0 = q['origin_um']; x1, y1 = x0 + w, y0 + h
    a = (x1 - x0) * (y1 - y0)
    bb = [min(bb[0], x0), min(bb[1], y0), max(bb[2], x1), max(bb[3], y1)]
    if BAY.search(q['type']) and not t.get('hard_cores'):
        bay += a; cnt['bay'] += 1
    else:
        slot += a; cnt['slot'] += 1
    for c in t.get('hard_cores') or []:
        ow = c.get('outline_um') or [0, 0]
        core += ow[0] * ow[1]
chan = A - slot - bay
out = dict(die=p['die'].get('name'), outline_um=[W, H], die_mm2=round(A / 1e6, 2),
           slot_mm2=round(slot / 1e6, 2), bay_mm2=round(bay / 1e6, 2), chan_mm2=round(chan / 1e6, 2),
           slot_pct=round(100 * slot / A, 1), bay_pct=round(100 * bay / A, 1), chan_pct=round(100 * chan / A, 1),
           core_slot_mm2=round(core / 1e6, 2), n=dict(cnt),
           bbox_inside=bb[0] >= -1e-3 and bb[1] >= -1e-3 and bb[2] <= W + 1e-3 and bb[3] <= H + 1e-3,
           reticle_858_margin_mm2=round(858 - A / 1e6, 1))
if len(sys.argv) > 2:
    R = json.load(open(sys.argv[2]))
    d = 0.0; nf = []
    for r in R:
        n = r.get('n_inst', 1); o = r.get('old') or [0, 0]; nw = r.get('new') or o
        d += n * (nw[0] * nw[1] - o[0] * o[1])
        if r.get('fits_parent') is False:
            nf.append((r['module'], r.get('decision'), r.get('bound')))
    dec = collections.Counter(r.get('decision') for r in R)
    out['reform'] = dict(rows=len(R), core_slot_delta_mm2=round(d / 1e6, 3), not_fit_parent=nf, decisions=dict(dec))
print(json.dumps(out))
