#!/usr/bin/env python3
"""KV-P8-PLAN 10-23: KV die plan v3.9 = v3.3 as-built view (plan_v33 patches) + two COORD rulings (KV-P8 23:3x):

 (1) v3.8 (a) PV control co-location, option ctlv4 (study bind/kv_pv_v38_ctl_options.json @04d827876, KV-P7-V38):
     the pair control leaf pvw_<i>__u_ctl moves from hub_C into pv_<S|N>_4 and ALL four vports of each quadrant side
     (vport_<Q>_0..3) move from the odd PV rows (pv_*_1/3/5/7) into pv_<S|N>_4 too.  V, cmd and flags then leave one
     partition and the vport header is local; the RH heads, the result trunk and pvfin stay in hub_C.
     (OT_V39_CTLV4=0 switches it off.)
 (2) ONE die re-floorplan that widens the four families with hard-core channels (hg, hgi, pc, pv) -- the KV die may grow
     up to reticle (owner 10-18).  The lattice column boundaries XB are re-derived from the per-column widths below;
     every partition of a column (incl. the hub-row and IO-row partitions above / below it) takes the column width, so
     the die stays fully abutted (no empty area).  Row height ROW may grow too (OT_V39_ROW).  The fault-OR hub
     assignment keeps the as-built x map (HUBX is computed before the patch), so no leaf moves because of geometry.

Widths are on the 8.64-um lattice.  Station counts: a crossing gets ceil(span / 750) ft stations (emit ST_MAX), so
hg / hgi / pc <= 1500 um and pv <= 2250 um keep the E-W station count of every straight crossing (2 / 2 / 2 / 3) and
ROW <= 2250 keeps the N-S count (3).

usage: plan_v39.py --asbuilt ASBUILT --out STAGE1.json.gz   (env: OT_V39_COLW='phy,pc,hg,hgi,pv', OT_V39_ROW, OT_V39_CTLV4)"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_v33  # noqa: E402,F401  (v3.2 + v3.3 patches)
import plan_v31 as pv  # noqa: E402

G = pv.G
COLW0 = dict(phy=864.0, pc=1036.8, hg=1278.72, hgi=1278.72, pv=1900.8)
COLW_V39 = dict(phy=864.0, pc=1209.6, hg=1494.72, hgi=1494.72, pv=2073.6)
ROW_V39 = 1520.64


def lat(v):
    return round(round(v / G) * G, 4)


def colw():
    w = dict(COLW_V39)
    if os.environ.get('OT_V39_COLW'):
        w = dict(zip(('phy', 'pc', 'hg', 'hgi', 'pv'), (float(x) for x in os.environ['OT_V39_COLW'].split(','))))
    return {k: lat(v) for k, v in w.items()}


def apply_geometry():
    w = colw()
    cols = [w['phy'], w['pc'], w['hg'], w['hgi'], w['pv'], w['hgi'], w['hg'], w['pc'], w['phy']]
    xb = [0.0]
    for c in cols:
        xb.append(round(xb[-1] + c, 4))
    row = lat(float(os.environ.get('OT_V39_ROW', ROW_V39)))
    pv.XB = xb
    pv.ROW = row
    pv.Y_BS = 8 * row
    pv.Y_BN = pv.Y_BS + pv.BAND
    pv.Y_N = pv.Y_BN + pv.BAND
    pv.Y_SYS = pv.Y_N + 8 * row
    pv.DIE_W, pv.DIE_H = xb[-1], pv.Y_SYS + pv.SYS_H
    return xb, row


XB_V39, ROW_V39_EFF = apply_geometry()

CTL_ROW = 4
_orig_assign = pv.assign_blocks


def assign_blocks(B):
    out = _orig_assign(B)
    if os.environ.get('OT_V39_CTLV4', '1') == '0':
        return out
    n_ctl = n_vp = 0
    for n in list(out):
        t = n.split('__')[0]
        rest = n[len(t):]
        m = re.match(r'pvw_([01])$', t)
        if m and re.match(r'__u_ctl(__|$)', rest):
            half = 'S' if m.group(1) == '0' else 'N'
            assert out[n][0] == 'hub_C', (n, out[n])
            out[n] = (f'pv_{half}_{CTL_ROW}', 'pv' + rest)
            n_ctl += 1
            continue
        m = re.match(r'vport_(WS|ES|WN|EN)_(\d+)$', t)
        if m:
            q, j = m.group(1), int(m.group(2))
            out[n] = (f'pv_{pv.QUADS[q][1]}_{CTL_ROW}', f'vport_{pv.QUADS[q][0]}{j}{rest}')
            n_vp += 1
    assert n_ctl >= 2 and n_vp >= 16, (n_ctl, n_vp)
    return out


pv.assign_blocks = assign_blocks


# trunk rule fix for pv-rooted trees (ctlv4): plan_v31.build sizes every pc/hg/hgi edge of a tap tree at the width
# needed at the tree's FIRST row partition below the root.  For a hub-rooted tree that is the column entry; for a tree
# rooted IN a pv row (vport / ctl now in pv_*_4) the first row partition is the next pv row, so a branch turning
# into the hgi/hg/pc row two pv rows down was sized for both rows (vq# 30 b on a 15-b ft slot: schema error).  The
# entry is the first NON-pv row partition (pv rows are the column itself).  Checked against the v3.3 stage1 with
# ctlv4 off: only the 16 pv-rooted vport vo trees change, and only their pv_*_0 -> hgi_*_0 -> hg_*_0 branch, which
# v3.3 sized at the full pv trunk (140..908 b) for 12 needed bits (an over-wide trunk into hgi/hg row 0).
import inspect  # noqa: E402
_src = inspect.getsource(pv.build)
_old = "if P[p]['cls'] in ('pc', 'hg', 'hgi', 'pv', 'phy'):"
assert _src.count(_old) == 1
exec(compile(_src.replace(_old, "if P[p]['cls'] in ('pc', 'hg', 'hgi', 'phy'):"), pv.__file__, 'exec'), pv.__dict__)

REF_STAGE1 = Path(__file__).resolve().parent / 'stage1_v33.json.gz'
_orig_build = pv.build


def build(asb):
    """stable lane ids: a lane with the same (src, port, root, hops) as in the v3.3 stage1 keeps its id; new lanes
    get ids after the v3.3 maximum, so downstream lane references (post_v37s L2045, R8 groups) still resolve."""
    import gzip
    import json
    S = _orig_build(asb)
    ref = json.load(gzip.open(REF_STAGE1, 'rt'))['lanes']

    def key(l):
        return (l['src'], l['sp'], l['root'], json.dumps(l['hops']))
    rid = {}
    for l in ref:
        assert key(l) not in rid, key(l)
        rid[key(l)] = l['id']
    nxt = 1 + max(int(l['id'][1:]) for l in ref)
    kept = new = 0
    for l in S['lanes']:
        k = key(l)
        if k in rid:
            l['id'] = rid.pop(k)
            kept += 1
        else:
            l['id'] = f'L{nxt}'
            nxt += 1
            new += 1
    S['lane_id_map'] = dict(kept=kept, new=new, retired=sorted(rid.values(), key=lambda x: int(x[1:])))
    sys.stderr.write(f'plan_v39: lanes kept {kept}, new {new}, retired {len(rid)}\n')
    return S


pv.build = build


if __name__ == '__main__':
    pv.main()
