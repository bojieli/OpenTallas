#!/usr/bin/env python3
"""Build results/arch/hbm_mtp_next_1018/sm_area/summary.json from the fetched per-run area.json + bench logs."""
import json, pathlib, sys, re
R = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2]); meta = json.loads(pathlib.Path(sys.argv[3]).read_text())
LEAVES = 16 * 32                         # d4g GEN2: 16 x ot_hbm_accel_smh_attn, each 8 columns x 2 tiles x 2 leaves
BDC_OUTLINE = 112.32 * 142.56            # closed smh_bdc_ref_p50 view outline (um2)
XS_MACRO = 94.824 * 41.040               # ot_sram_1r1w_128x256_m1_r2c2 LEF (um2); x store = 4 per leaf (128 x 788 b)
def ld(n):
    p = R / n / 'area.json'
    return json.loads(p.read_text()) if p.is_file() else None
base = {u: ld(f'{u}_base') for u in ('bdc', 'tcc')}
util = base['bdc']['synthesis']['cell_area_um2'] / BDC_OUTLINE
rows = {}
for u in ('bdc', 'tcc'):
    b1 = ld(f'{u}_p1')
    for p in (1, 2, 4, 6, 8):
        d = ld(f'{u}_p{p}')
        if d is None: rows.setdefault(u, {})[p] = {'status': 'MISSING'}; continue
        s, t = d['synthesis'], d['sta_tt']
        a, f = s['cell_area_um2'], s['sequential_cell_count']
        da = a - b1['synthesis']['cell_area_um2']; df = f - b1['synthesis']['sequential_cell_count']
        rows.setdefault(u, {})[p] = {
            'cell_area_um2': round(a, 1), 'flops': f, 'seq_area_um2': round(s['sequential_area_um2'], 1),
            'delta_area_vs_p1_um2': round(da, 1), 'delta_flops_vs_p1': df,
            'area_per_added_lane_um2': round(da / (p - 1), 1) if p > 1 else None,
            'flops_per_added_lane': round(df / (p - 1), 1) if p > 1 else None,
            'area_ratio_vs_p1': round(a / b1['synthesis']['cell_area_um2'], 3),
            'added_die_mm2_logic': round(da / util * LEAVES / 1e6, 2),
            'tt_setup_wns_ns_unbuffered_synth': round(t['setup_wns_ns'], 3),
            'critical_path_ns_unbuffered_synth': round(t['critical_path_ns'], 3),
            'canonical_sha256': d['canonical_sha256'], 'mem_cells': d['checks']['mem_cells_in_stat'],
            'job': meta['jobs'].get(f'synth_{u}_p{p}')}
xs_per_lane_mm2 = 4 * XS_MACRO * LEAVES / 1e6
summ = {}
for p in (1, 2, 4, 6, 8):
    bd = rows['bdc'][p]['added_die_mm2_logic']; tc = rows['tcc'][p].get('added_die_mm2_logic'); est = False
    if tc is None:   # tcc synthesis still running: linear in lanes from the largest measured P (bdc and tcc P<=4 are linear)
        pm = max(q for q in rows['tcc'] if 'added_die_mm2_logic' in rows['tcc'][q])
        tc = round(rows['tcc'][pm]['added_die_mm2_logic'] / (pm - 1) * (p - 1), 2); est = True
    lg = bd + tc
    summ[p] = {'tcc_estimated_linear': est, 'added_die_mm2_tcc_logic': tc,'added_die_mm2_bdc_plus_tcc_logic': round(lg, 2),
               'added_die_mm2_bdc_only_logic': rows['bdc'][p]['added_die_mm2_logic'],
               'added_die_mm2_xstore_replicated': round((p - 1) * xs_per_lane_mm2, 2),
               'added_die_mm2_total_incl_xstore': round(lg + (p - 1) * xs_per_lane_mm2, 2),
               'pct_of_die_641p83': round(100 * (lg + (p - 1) * xs_per_lane_mm2) / 641.83, 1)}
res = {'schema': 'opentallas.hbm_mtp_next_1018.sm_area.v1', 'agent': 'MTP-AREA (Claude) 2026-10-18',
       'scope': 'sizing only: Yosys 0.68 flatten + ABC mapped std-cell area (ASAP7 RVT TT, 0.833 ns target), OpenSTA '
                'on the unplaced, unbuffered netlist; no placement, no routing, not bound into any die',
       'source': meta['source'],
       'current_tile': {'die': 'd4g GEN2 (hbm_v16_die, /home/ubuntu/artifacts/hdie-d4/d4g_gen2/pb0/port_bind.json)',
                        'sm_master': 'ot_hbm_accel_smh_attn x16 (rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv)',
                        'leaf': 'ot_hbm_sm_attn_leafh: x store ot_hbm_accel_smh_xs + block-dot ot_hbm_accel_smh_bdc + BF16 column (tcl halves + tct)',
                        'leaves_per_die': LEAVES, 'fp8_macs_per_bdc': 64, 'bf16_macs_per_tcc': 16,
                        'closed_bdc_view': 'physical/ref_tile/smh_bdc_ref_p50 outline 112.32 x 142.56 um = %.1f um2' % BDC_OUTLINE,
                        'baseline_production_synth': {u: {'cell_area_um2': round(base[u]['synthesis']['cell_area_um2'], 1),
                                                          'flops': base[u]['synthesis']['sequential_cell_count']} for u in base}},
       'die_translation': {'rule': 'added_die_mm2 = delta cell area / util x 512 leaves; util = baseline bdc synth cell area / closed bdc outline',
                           'util': round(util, 4), 'die_area_mm2': 641.83,
                           'xstore_note': 'each lane needs its own activation operand stream: replicating the leaf x store (4 x 128x256 SRAM, %.0f um2/leaf) costs %.2f mm2 per added lane die-wide; alternative is a P-wide read of a shared deeper store (same macro count growth for the same K capacity)' % (4 * XS_MACRO, xs_per_lane_mm2)},
       'per_unit': rows, 'per_P': summ, 'bench': meta['bench'], 'jobs': meta['jobs']}
out.write_text(json.dumps(res, indent=1) + '\n'); print(json.dumps(summ, indent=1))
for u in rows:
    for p, r in rows[u].items(): print(u, p, {k: r.get(k) for k in ('cell_area_um2', 'flops', 'area_per_added_lane_um2', 'flops_per_added_lane', 'tt_setup_wns_ns_unbuffered_synth')})
