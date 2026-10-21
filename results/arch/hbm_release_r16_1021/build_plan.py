#!/usr/bin/env python3
"""HBM-OWN/DIE 10-21 r16 floorplan = r15 planB_h158 (successor 77afa7aee) + structural capacity fixes from the r15 h158
S4 classification (lanes/HBM-OWN.md "DIE 12:50"): S4 92 hops (64 = VM hub vmh_* abutted members), 47 overfull
station windows (SU pgslice_lg / pslice / sfucore / hc bankq / N stripe / idx score NW).

    build_plan.py VARIANT OUT     VARIANT = M (main) | F (fallback)
  1 X channel cuts (d4g_channel_cuts.py): +172.8 um at x 7300 and x 17900 in EVERY band (W/E SU|SFU column gaps,
    SM2|SM1 and SM6|SM5 gaps, stripes consistent with the PHY/PC row) -> die +345.6 um X, Y unchanged (reticle margin).
  2 idx score escape: hb_idx__s_NW / hb_idx__s_NE +259.2 um Y inside their idxs_N* plan block (SMH gap 146 -> 405 um).
  3 wider die ft grid (d4g_ft_grid.py --select) in the capacity-hot SYNTH masters: M 64.8 um, F 86.4 um channels.
  4 VM hub relay channels: grants floorplan.region_halo {'^vmh_': M 21.6 | F 32.4} (die_case_v16 region placement).
"""
import copy, json, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v16'))
from d4g_channel_cuts import overlaps, wh  # noqa: E402

var, out = sys.argv[1], Path(sys.argv[2])
BASE = ROOT / 'results/arch/hbm_release_r15_1021/planB_h158'
FT_W = {'M': 64.8, 'F': 86.4}[var]; HALO = {'M': 21.6, 'F': 32.4}[var]
HOT = r'^(ot_hbm_su_static_pgslice_lg|ot_hbm_su_programme_pslice_c5|ot_hbm_idx_score_quarter_static|ot_hgi_sfu_core_split3|' \
      r'ot_hgi_sfu_programme_store_r10|ot_hbm_hc_bankq|ot_hbm_svc_wb_kport_q)'
tmp = out.parent / (out.name + '.cuts'); shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(out, ignore_errors=True)
cuts = [[7300.0, 172.8], [17900.0, 172.8]]
step = dict(plan='R16_' + var, why='HBM-OWN/DIE 10-21: r15 h158 S4 capacity (47 windows SU/SFU columns): +172.8 X channels at '
            'x 7300 / 17900 in every band; Y unchanged (reticle 500 um margin)',
            bands=[dict(name='all', y0=-1e9, y1=1e9, cuts=cuts)], ycuts=[])
spec_p = out.parent / f'cut_spec_{var}.json'; out.parent.mkdir(parents=True, exist_ok=True); spec_p.write_text(json.dumps(step, indent=1))
subprocess.run([sys.executable, str(ROOT / 'tools/hbm_die_v16/d4g_channel_cuts.py'), '--spec', str(spec_p),
                '--grants', str(BASE / 'grants_d4g.json'), '--plan', str(BASE / 'compact.P.json'), '--lanes', str(BASE / 'lanes.json'),
                '--region-map', str(BASE / 'd4g_region_map.json'), '--out', str(tmp)], check=True)
# compose the coord map: old steps + this step (GEN --coord-map maps ORIGINAL contract-note homes)
cm0 = json.load(open(BASE / 'coord_map.json')); cm = copy.deepcopy(cm0)
cm['spec']['steps'] = cm0['spec']['steps'] + [step]; cm['r16'] = dict(added_step='R16_' + var, by='HBM-OWN/DIE')
G = json.load(open(tmp / 'grants_d4g.json')); G0 = json.load(open(BASE / 'grants_d4g.json'))
fp0 = G0['floorplan']; fp = G['floorplan']
fp['channel_cuts_history'] = [fp0.get('channel_cuts'), fp['channel_cuts']]; fp['channel_cuts'] = fp0.get('channel_cuts')
fp['channel_cuts_r16'] = dict(tool='tools/hbm_die_v16/d4g_channel_cuts.py', spec=step, from_die_um=fp0['die_um'])
# 2 score escape
mv = {}
for s in G['slots']:
    if s['name'] in ('hb_idx__s_NW', 'hb_idx__s_NE'):
        s['origin']['y'] = round(s['origin']['y'] + 259.2, 3); mv[s['name']] = dict(s['origin'])
srs = lambda GG: [(s['name'], s['origin']['x'], s['origin']['y']) + wh(s) for s in GG['slots'] if s.get('kind') != 'die']
G_cut = json.load(open(tmp / 'grants_d4g.json'))
new_ov = set(map(frozenset, overlaps(srs(G)))) - set(map(frozenset, overlaps(srs(G_cut))))
if new_ov:
    raise SystemExit(f'R16 score escape overlaps {sorted(map(sorted, new_ov))}')
H = fp['die_um'][1]
for n, o in mv.items():
    assert o['y'] + 1512.0 <= H, (n, o)
fp['score_escape_r16'] = dict(moved=mv, dy_um=259.2, why='r14 window 5.99 / r15 1.68 at hb_idx__s_NW; SMH gap 146 -> 405 um')
# 4 VM hub region halo
fp['region_halo'] = {'^vmh_': HALO}
out.mkdir(parents=True)
for f in ('compact.P.json', 'lanes.json', 'd4g_region_map.json'):
    shutil.copy2(tmp / f, out / f)
for f in ('cxdl_bay_report.json', 'prior_cxdl_only_placement_check.json'):
    if (BASE / f).exists():
        shutil.copy2(BASE / f, out / f)
json.dump(cm, open(out / 'coord_map.json', 'w'), indent=1)
shutil.copy2(tmp / 'report.json', out / 'channel_cuts_report.json'); shutil.copy2(tmp / 'plan.png', out / 'channel_cuts.png')
pre = out.parent / (out.name + '.pre_ft'); shutil.rmtree(pre, ignore_errors=True); pre.mkdir()
json.dump(G, open(pre / 'grants_d4g.json', 'w'), indent=1)
# 3 ft grid widen (hot SYNTH masters only)
subprocess.run([sys.executable, str(ROOT / 'tools/hbm_die_v16/d4g_ft_grid.py'), '--plan-dir', str(pre), '--out', str(pre / 'ft'),
                '--width', str(FT_W), '--select', HOT], check=True)
shutil.copy2(pre / 'ft/grants_d4g.json', out / 'grants_d4g.json'); shutil.copy2(pre / 'ft/ft_grid_report.json', out / 'ft_grid_r16_report.json')
if (pre / 'ft/ft_grid.png').exists():
    shutil.copy2(pre / 'ft/ft_grid.png', out / 'ft_grid_r16.png')
shutil.rmtree(pre); shutil.rmtree(tmp)
print('R16_PLAN', var, out, 'die', fp['die_um'], 'halo', HALO, 'ft', FT_W)
