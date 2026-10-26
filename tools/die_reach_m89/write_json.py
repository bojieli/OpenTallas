#!/usr/bin/env python3
"""REACH-M89: analysis.json + GRT check -> results/arch/die_reach_m89_1022.json"""
import json, sys
A = json.load(open(sys.argv[1])); out = sys.argv[2]
LEGAL = (150, 200, 250, 300, 450)            # spacings whose max slew stays <= 320 ps (liberty max_transition)
summary = {}
for cell, a in A.items():
    ar, dm = a['calc']['arnoldi'], a['calc']['dmp_ceff_elmore']
    row = dict(relay=cell, o_eff_launch_ps=ar['M8/BUFx12f_ASAP7_75t_R/300']['launch_to_rep1_ps'])
    for lay in ('M8', 'M9'):
        cands = [(k, r) for k, r in ar.items() if r['layer'] == lay and r['spacing_um'] in LEGAL and r['slew_legal_320']]
        k, r = max(cands, key=lambda kr: kr[1]['reach_um'])
        kc, rc = max(cands, key=lambda kr: kr[1]['reach_um_calibrated'])
        row[lay] = dict(best=k, reach_um=r['reach_um'], stage_ps_per_um=r['stage_ps_per_um'],
                        best_calibrated=kc, reach_um_calibrated=rc['reach_um_calibrated'],
                        bufx12f_300=dict(reach_um=ar[f'{lay}/BUFx12f_ASAP7_75t_R/300']['reach_um'],
                                         reach_um_calibrated=ar[f'{lay}/BUFx12f_ASAP7_75t_R/300']['reach_um_calibrated']),
                        bufx16f_600_slew_illegal=dict(reach_um=ar[f'{lay}/BUFx16f_ASAP7_75t_R/600']['reach_um'],
                                                      max_slew_ps=ar[f'{lay}/BUFx16f_ASAP7_75t_R/600']['max_slew_ps']))
    row['M45_BUFx8_160_check'] = dict(reach_um=ar['M45/BUFx8_ASAP7_75t_R/160']['reach_um'],
                                      reach_um_calibrated=ar['M45/BUFx8_ASAP7_75t_R/160']['reach_um_calibrated'])
    summary.setdefault(a['die'], []).append(row)
die_min = {}
for die, rows in summary.items():
    die_min[die] = dict(
        reach_um_M8M9_model_min=min(min(r['M8']['reach_um'], r['M9']['reach_um']) for r in rows),
        reach_um_M8M9_calibrated_min=min(min(r['M8']['reach_um_calibrated'], r['M9']['reach_um_calibrated']) for r in rows),
        relays=[r['relay'] for r in rows])
doc = {
 'schema': 'opentallas.die_reach_m89.v1', 'date': '2026-10-22', 'lane': 'REACH-M89 (owner-approved measurement)',
 'question': 'per-cycle relay reach of a die wire on M8/M9 with optimal repeaters (ASAP7 TT, T 833.333); is a 1.0-2.0 mm relay hop feasible?',
 'method': {
  'model': 'self-pair hop: launch relay ETM (worst o bit, TT lib, ideal ck) -> via stack relay pin layer->M1 + 5 um M4 -> repeater #1 adjacent to the relay -> [via M1->Mx, d um Mx, via Mx->M1, repeater]* -> last <= d um Mx -> via Mx->relay pin layer -> capture relay ETM (worst setup bit). Wires = distributed RC ladders (<=10 um sections) with setRC.tcl per-layer R/C; vias lumped (set_layer_rc -via). Clock 833.333, uncertainty 150 = U 60 + SKEW 90 (die_reach_1016 formula). The 26Q3 OpenSTA in openroad/orfs:asap7lock applies the ETM min_clock_tree_path at capture (macro clock tree delay), which reproduces pair_check o = O - R, s = S + R (rly_266_SN o+s 328 ps here vs 337.5 in die_reach_1016).',
  'sweep': 'layers M8, M9; BUFx8 / BUFx12f / BUFx16f; spacing 100,150,200,250,300,450,600,800,1000 um; L 200..3000 step 50; reach = first failing L interpolated (slack >= 0 for all shorter L). Delay calc arnoldi (headline) and dmp_ceff_elmore.',
  'calibration': 'the same model on the 0.76 ps/um source config (M4/M5 avg RC, BUFx8 every 160 um) gives 0.6315 ps/um, i.e. 0.76 carries 1.20x margin. reach_um_calibrated multiplies the repeated-wire delay by 0.76/0.6315 = 1.203 (same margin as today\'s planning constant). M45 check rows reproduce die_reach_1016 within ~5-10% after calibration (e.g. rly_266_SN 477 vs 455, qfd_cst_n 465 vs 425, rlys_296 497 vs 446, hbfd_rly_48 452 vs 413-421).',
  'slew_rule': 'liberty max_transition 320 ps: spacing >= 600 um gives 330-430 ps (illegal, and beyond table range); 800/1000 um give 550-1030 ps. Legal spacing <= ~450-500 um.',
  'tools': 'tools/die_reach_m89/{gen.py,analyse.py,grt_case.py,write_json.py}; runs via ot-run (ot-agidock128 sweep, ot-pve1 GRT), scratch /srv/opentallas-scratch/claude/reach-m89-1022',
 },
 'grt_validation': {
  'case': 'placed die 1.6-1.9 mm, S81 dsfd_dvrlyh_276_NS relays, H hop (M8) + V hop (M9); GRT with M2-M7 capacity adjusted to 0 (pins lifted by vias), estimate_parasitics -global_routing (setRC.tcl), dmp_ceff_elmore',
  'results_slack_ps': {
   'L1500_d300_BUFx12f': {'M8': {'grt': 79.8, 'model_arnoldi': 77.4, 'model_dmp': 94.0}, 'M9': {'grt': 92.2, 'model_arnoldi': 92.8, 'model_dmp': 109.0}},
   'L1200_d600_BUFx16f': {'M8': {'grt': 85.5, 'model_arnoldi': 83.7, 'model_dmp': 105.0}, 'M9': {'grt': 101.4, 'model_arnoldi': 101.3, 'model_dmp': 121.9}}},
  'grt_stage': 'M8 BUFx12f 300 um stage 83 ps (0.277 ps/um), 33.6 fF wire+pin',
  'verdict': 'GRT-routed slack matches the arnoldi model within 2.4 ps (dmp model is 15-20 ps optimistic); headline numbers use arnoldi',
 },
 'per_relay': summary,
 'per_die_min': die_min,
 'answer': {
  'ps_per_um': 'optimal repeaters: BUFx12f every 200-300 um -> 0.267-0.285 ps/um (M9 slightly better than M8); 450 um 0.30-0.32; 600 um 0.34-0.37 (slew-illegal); vs 0.76 for today\'s M4/M5 160 um assumption (0.63 measured by the same model)',
  'hop_1mm': 'FEASIBLE on all four dies on M8/M9 with BUFx12f every 200-300 um, even with the 1.20x calibration margin (worst: hbm hbfd_rly_48 1.00-1.01 mm calibrated, 1.18-1.23 mm model)',
  'hop_1p5mm': 'model-feasible for S81 dvrlyh_276 (1.80-1.83 mm), qwen_kv (1.44-1.50) and hbm rly_624 (1.41-1.46); calibrated only S81 dvrlyh_276 (1.50-1.53). Not for qwen_compute qfd_cst_n (1.26-1.27 model) or hbm rly_48 / S81 rly_266.',
  'hop_2mm': 'NOT feasible in one cycle on any die (best 1.83 mm model, S81 dvrlyh_276 on M9)',
  'caveat_block_crossing': 'repeaters must sit every <= ~450-500 um (slew 320 ps). A lane cannot cross a 1.5-3.5 mm hard block on M8/M9 unrepeated: block-edge-only relaying (1-3.5 mm unbuffered span) is slew-illegal (>=550 ps at 800 um, >1 ns at 1 mm). Crossing blocks needs repeater islands / feedthrough buffer sites inside the blocks (M1-M7 via access at <=450 um pitch) or blocks <= ~500 um between rows.',
  'relay_quality': 'reach is dominated by the relay launch ETM: dvrlyh_276 o_eff 136 ps -> 1.8 mm; rly_266 / hbfd_rly_48 / qfd_cst_n o_eff 197-231 ps -> 1.2-1.3 mm',
 },
}
json.dump(doc, open(out, 'w'), indent=1)
print(json.dumps(die_min, indent=1))
