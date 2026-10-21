#!/usr/bin/env python3
"""HBM-OWN/DIE2 10-21 r16b floorplan = r15 planB_h158 (successor 77afa7aee) + r16 capacity fixes + STRUCTURAL fixes from the
r16 quick S4 (lanes/HBM-OWN.md "DIE 13:10" / "DIE2"): M 49 hops / 2033 forced / 36 windows, F 41 / 1974 / 36.

    build_plan_b.py VARIANT OUT     VARIANT = bM (main) | bF (fallback, bolder)

Reticle: tools/hbm_die_v15/reticle.py (owner 10-16, >= 500 um margin in W AND H) -> die <= 25500 x 32500: r16 already used
X +345.6 and Y has 35 um left, so r16b does NOT grow the die; it re-orients / re-packs / re-allocates the same X budget.
  1 SM ORIENTATION (root cause of the smh_attn SM0/SM2 windows 2.45/1.86 and of most xq_p1 stack demand): every SM was
    R0/MX, so the odd SMs (sm_<row>1/3/5/7) had their xq-stack face (E) pointing AWAY from their xq stack into the SM-pair
    slit (xq_SW_p0_eg.xw 2055 b -> sm_SW1 47 stages vs 14 to sm_SW0 -> 33 equal-age pad stages booked at sm_SW0's face),
    and the ONE shared SYNTH abstract averaged opposite peer directions (xq E for even / W for odd, above for S row / below
    for N row) -> its pins sat mid-face.  r16b: S row even R0 / odd MY, N row even MX / odd R180, so in the tile frame every
    SM sees its xq stack E-and-N and its svg/xc stripe S (floorplan.sm_orient_exact: GEN keeps these orients).
  2 pgp_SE lifted out of the east lk/ep lane band (r15/r16 die-worst window [22000,15400] = ep_S3<->hb_coll_SE +
    hcollks_SE funnel past pgp_SE): pgp_SE bottom = lk row top + 86.4.
  3 PHY-SD 12:15: each ep abutted inboard of its lk (21.6 um), pairs 86.4 apart; east pairs MY (lk core face W, ep link face E).
  4 VM hub: vmh_SW/NW grant slots and vmh_SE/NE plan blocks widened (GEN r16 overflowed 7/8 vmdel lanes out of the region).
  bM: r16 M cuts (x 7300 / 17900 +172.8 every band), halo 21.6, ft 64.8 (r16 hot masters).
  bF: X budget re-allocated to both sides of the two OUTER xq/xl stacks (x 3950/4800 and 20300/21170, +86.4 each, every
      band; PHY/PC span 8063-17060 untouched) instead of the SU cuts that did not move the SU windows; halo 32.4; ft 86.4
      incl. smh_attn columns.
"""
import copy, json, re, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v16'))
from d4g_channel_cuts import overlaps, wh  # noqa: E402

var, out = sys.argv[1], Path(sys.argv[2])
BASE = ROOT / 'results/arch/hbm_release_r15_1021/planB_h158'
CFG = {
    # c*: + xl_<q>_ctl (+ its two aq trees) moved to the MIDPOINT of its two xq stacks in the 459 um gap band between the SM row
    #     and the middle band: xl_ctl broadcasts c_d 1024 b (+ aq q 2x256 b) to BOTH stacks; at the outer stack the near
    #     sink took 15-20 equal-age pad stages x 2 tiles (xl_*_ctl pads 1.15 mm2 = the outer-stack windows 1.9-2.06).
    'bM': dict(ft=64.8, halo=21.6, cuts=[[7300.0, 172.8], [17900.0, 172.8]], hot_extra=''),
    'bF': dict(ft=86.4, halo=32.4, cuts=[[3950.0, 86.4], [4800.0, 86.4], [20300.0, 86.4], [21170.0, 86.4]],
               hot_extra='|ot_hbm_accel_smh'),
}
CFG['cM'] = dict(CFG['bM'], xlmid=True); CFG['cF'] = dict(CFG['bF'], xlmid=True)
# d*: + pgp_NW / pgp_SE (2470 b command to their 4 su_<q><g>) moved into the gap between their two SU columns (r16b: pgp_NW at
#     the die W edge -> 148k um2 of equal-age pads on su_NW2's window 1.70; pgp_SE beside the east lk/ep row)
CFG['dM'] = dict(CFG['cM'], pgpmid={'pgp_NW': (3610.8, 17085.6), 'pgp_SE': (20520.0, 14601.6)})
CFG['dF'] = dict(CFG['cF'], pgpmid={'pgp_NW': (3610.8, 17085.6), 'pgp_SE': (20520.0, 14601.6)})
CFG = CFG[var]
FT_W, HALO = CFG['ft'], CFG['halo']
HOT = r'^(ot_hbm_su_static_pgslice_lg|ot_hbm_su_programme_pslice_c5|ot_hbm_idx_score_quarter_static|ot_hgi_sfu_core_split3|' \
      r'ot_hgi_sfu_programme_store_r10|ot_hbm_hc_bankq|ot_hbm_svc_wb_kport_q' + CFG['hot_extra'] + ')'
tmp = out.parent / (out.name + '.cuts'); shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(out, ignore_errors=True)
step = dict(plan='R16_' + var, why='HBM-OWN/DIE2 10-21 r16b: X cuts ' + json.dumps(CFG['cuts']) + ' in every band; Y unchanged '
            '(reticle 500 um margin)', bands=[dict(name='all', y0=-1e9, y1=1e9, cuts=CFG['cuts'])], ycuts=[])
spec_p = out.parent / f'cut_spec_{var}.json'; out.parent.mkdir(parents=True, exist_ok=True); spec_p.write_text(json.dumps(step, indent=1))
subprocess.run([sys.executable, str(ROOT / 'tools/hbm_die_v16/d4g_channel_cuts.py'), '--spec', str(spec_p),
                '--grants', str(BASE / 'grants_d4g.json'), '--plan', str(BASE / 'compact.P.json'), '--lanes', str(BASE / 'lanes.json'),
                '--region-map', str(BASE / 'd4g_region_map.json'), '--out', str(tmp)], check=True)
cm0 = json.load(open(BASE / 'coord_map.json')); cm = copy.deepcopy(cm0)
cm['spec']['steps'] = cm0['spec']['steps'] + [step]; cm['r16'] = dict(added_step='R16_' + var, by='HBM-OWN/DIE2')
G = json.load(open(tmp / 'grants_d4g.json')); G0 = json.load(open(BASE / 'grants_d4g.json'))
P = json.load(open(tmp / 'compact.P.json'))
fp0 = G0['floorplan']; fp = G['floorplan']
fp['channel_cuts_history'] = [fp0.get('channel_cuts'), fp['channel_cuts']]; fp['channel_cuts'] = fp0.get('channel_cuts')
fp['channel_cuts_r16'] = dict(tool='tools/hbm_die_v16/d4g_channel_cuts.py', spec=step, from_die_um=fp0['die_um'])
W_, H_ = fp['die_um']
S = {s['name']: s for s in G['slots']}
srs = lambda GG: [(s['name'], s['origin']['x'], s['origin']['y']) + wh(s) for s in GG['slots'] if s.get('kind') != 'die']
prs = lambda PP: [('P:' + k, b['x'], b['y'], b['w'], b['h']) for k, b in PP.items() if isinstance(b, dict) and 'x' in b]
ov0 = set(map(frozenset, overlaps(srs(G) + prs(P))))
moves = {}


def move(n, x=None, y=None, orient=None, w=None):
    """move slot n (and its same-name plan block) to origin x/y, orient, width w"""
    rec = {}
    if n in S:
        o = S[n]['origin']
        if x is not None: o['x'] = round(x, 3)
        if y is not None: o['y'] = round(y, 3)
        if orient is not None: o['orient'] = orient
        if w is not None: S[n]['outline']['w'] = round(w, 3)
        rec['slot'] = dict(o, w=wh(S[n])[0], h=wh(S[n])[1])
    if isinstance(P.get(n), dict):
        b = P[n]
        if x is not None: b['x'] = round(x, 3)
        if y is not None: b['y'] = round(y, 3)
        if orient is not None and 'orient' in b: b['orient'] = orient
        if w is not None: b['w'] = round(w, 3)
        rec['plan'] = dict(b)
    if not rec:
        raise SystemExit(f'R16B no slot/plan block {n}')
    moves[n] = rec


def box(n):
    if n in S:
        w, h = wh(S[n]); return S[n]['origin']['x'], S[n]['origin']['y'], w, h
    b = P[n]; return b['x'], b['y'], b['w'], b['h']


# 1 SM orientation (tile frame: xq stack E+N, svg/xc stripe S for all 16)
for n in sorted(S):
    m = re.fullmatch(r'sm_([NS])W(\d)', n)
    if m:
        odd = int(m.group(2)) % 2 == 1
        move(n, orient=('MY' if odd else 'R0') if m.group(1) == 'S' else ('R180' if odd else 'MX'))
fp['sm_orient_exact'] = dict(by='HBM-OWN/DIE2 r16b', rule='S row even R0 / odd MY, N row even MX / odd R180: every SM sees its xq '
                             'stack E+N and its stripe S in the tile frame (shared SYNTH abstract)')
# 3 lk/ep re-pack (row y unchanged): west lk_S0|ep_S0 lk_S1|ep_S1 lk_N0|ep_N0 from lk_S0's x; east (lk MY core face W)
AB, PAIR = 21.6, 86.4
x = box('lk_S0')[0]
for lk, ep in (('lk_S0', 'ep_S0'), ('lk_S1', 'ep_S1'), ('lk_N0', 'ep_N0')):
    move(lk, x=x, orient='R0'); x += box(lk)[2] + AB
    move(ep, x=x, orient='R0'); x += box(ep)[2] + PAIR
xr = box('lk_S3')[0] + box('lk_S3')[2]
for lk, ep in (('lk_S3', 'ep_S3'), ('lk_N2', 'ep_N2')):
    xr -= box(lk)[2]; move(lk, x=xr, orient='MY'); xr -= AB
    xr -= box(ep)[2]; move(ep, x=xr, orient='MY'); xr -= PAIR
# 2 pgp_SE above the lk/ep lane band
row_top = max(box(n)[1] + box(n)[3] for n in ('lk_N2', 'lk_S3', 'ep_N2', 'ep_S3'))
move('pgp_SE', y=round((row_top + 86.4) / 0.216) * 0.216)
# 4 VM hub regions wider (slot regions grow E, plan-block regions grow W; 388.8 um = 9 x 43.2)
for n, grow_w in (('vmh_SW', False), ('vmh_NW', False), ('vmh_SE', True), ('vmh_NE', True)):
    x0, y0, w0, h0 = box(n)
    if grow_w:
        move(n, x=x0 - 388.8, w=w0 + 388.8)
    else:
        move(n, w=w0 + 388.8)
# 5 (c*) xl_ctl + aq trees at the stack midpoint in the SM-row / middle-band gap band
if CFG.get('xlmid'):
    for q in ('SW', 'SE', 'NW', 'NE'):
        cx = [box(f'xq_{q}_p{k}_bfq0')[0] + box(f'xq_{q}_p{k}_bfq0')[2] / 2 for k in (0, 1)]
        sm = [box(n) for n in S if re.fullmatch(rf'sm_{q[0]}W\d', n)]
        mid_b = [box(n) for n in ('su_' + q + '1', 'sfucore_' + q) if n in S]
        if q[0] == 'S':
            g0 = max(b[1] + b[3] for b in sm); g1 = min(b[1] for b in mid_b)
        else:
            g0 = max(b[1] + b[3] for b in mid_b); g1 = min(b[1] for b in sm)
        xc = (cx[0] + cx[1]) / 2; w, h = box(f'xl_{q}_ctl')[2:]
        assert g1 - g0 >= h + 43.2, (q, g0, g1)
        x0 = round((xc - w / 2) / 0.216) * 0.216; y0 = round(((g0 + g1) / 2 - h / 2) / 0.216) * 0.216
        move(f'xl_{q}_ctl', x=x0, y=y0)
        ax = x0 + w + 21.6
        for k, n in enumerate((f'xl_{q}_aqlo', f'xl_{q}_aqhi')):
            aw, ah = box(n)[2:]
            move(n, x=round(ax / 0.216) * 0.216, y=round(((g0 + g1) / 2 + (-ah - 10.8 if k == 0 else 10.8)) / 0.216) * 0.216)
    fp['xl_mid_r16c'] = dict(by='HBM-OWN/DIE2', why='xl_ctl c_d/aq broadcast to both xq stacks: midpoint removes the near-stack pads')
for n, (x_, y_) in (CFG.get('pgpmid') or {}).items():
    move(n, x=x_, y=y_, orient='R0')
# overlap / die checks (only NEW pairs vs the cut plan count)
ov1 = set(map(frozenset, overlaps(srs(G) + prs(P))))
new = sorted(map(sorted, ov1 - ov0))
new = [p for p in new if not (p[0].lstrip('P:') == p[1].lstrip('P:'))]
if new:
    raise SystemExit(f'R16B new overlaps {new[:20]} (+{len(new) - 20 if len(new) > 20 else 0})')
for n, r in moves.items():
    x0, y0, w0, h0 = box(n)
    assert 0 <= x0 and x0 + w0 <= W_ and 0 <= y0 and y0 + h0 <= H_, (n, x0, y0, w0, h0)
fp['r16b_moves'] = dict(by='HBM-OWN/DIE2', moves=moves)
# r16 score escape (kept)
mv = {}
for s in G['slots']:
    if s['name'] in ('hb_idx__s_NW', 'hb_idx__s_NE'):
        s['origin']['y'] = round(s['origin']['y'] + 259.2, 3); mv[s['name']] = dict(s['origin'])
ov2 = set(map(frozenset, overlaps(srs(G) + prs(P))))
if ov2 - ov1:
    raise SystemExit(f'R16B score escape overlaps {sorted(map(sorted, ov2 - ov1))}')
fp['score_escape_r16'] = dict(moved=mv, dy_um=259.2, why='r14 window 5.99 / r15 1.68 at hb_idx__s_NW; SMH gap 146 -> 405 um')
fp['region_halo'] = {'^vmh_': HALO}
out.mkdir(parents=True)
json.dump(P, open(out / 'compact.P.json', 'w'), indent=1)
for f in ('lanes.json', 'd4g_region_map.json'):
    shutil.copy2(tmp / f, out / f)
for f in ('cxdl_bay_report.json', 'prior_cxdl_only_placement_check.json'):
    if (BASE / f).exists():
        shutil.copy2(BASE / f, out / f)
json.dump(cm, open(out / 'coord_map.json', 'w'), indent=1)
shutil.copy2(tmp / 'report.json', out / 'channel_cuts_report.json'); shutil.copy2(tmp / 'plan.png', out / 'channel_cuts.png')
pre = out.parent / (out.name + '.pre_ft'); shutil.rmtree(pre, ignore_errors=True); pre.mkdir()
json.dump(G, open(pre / 'grants_d4g.json', 'w'), indent=1)
subprocess.run([sys.executable, str(ROOT / 'tools/hbm_die_v16/d4g_ft_grid.py'), '--plan-dir', str(pre), '--out', str(pre / 'ft'),
                '--width', str(FT_W), '--select', HOT], check=True)
shutil.copy2(pre / 'ft/grants_d4g.json', out / 'grants_d4g.json'); shutil.copy2(pre / 'ft/ft_grid_report.json', out / 'ft_grid_r16_report.json')
if (pre / 'ft/ft_grid.png').exists():
    shutil.copy2(pre / 'ft/ft_grid.png', out / 'ft_grid_r16.png')
shutil.rmtree(pre); shutil.rmtree(tmp)
print('R16B_PLAN', var, out, 'die', fp['die_um'], 'halo', HALO, 'ft', FT_W, 'moves', len(moves))
