# core4_sfu2_b3624: v5 plan, measured SFU core 763.56 × 3,580

**ADOPTED** into `results/arch/hier_contract_1015/hbm_v15.json` (version 8) by H-DIE-V790 on 10-16, on the H-DIE
decision. The rehome audit found 0 slots outside the die, 0 overlaps and 0 points in hard blocks. The v4 plan is
`../core4_sfu2_su2825`, the previous homes.

## What changed from v4
- **SFU core:** `sfucore_<q>` is 763.56 × 3,580 (H-SU: the cluster-legal lane view is 216 wide, 3 per row).
- **Band:** 3,624.48 (+471.2).
- **SFU store:** `sfus_<q>` stays 1,020 × 1,412, at y offset 2,190.88. It is 21.6 µm below the band top, above the
  group-2 hc/sfu leaves.
- **Die:** 32,990 × 25,107.608 µm = **828.3 mm²** (+31.1 mm²).
- **Unchanged from v4:**
  - SM slot 7,200 × 1,800 and SU slot 1,797.12 × 2,825.28;
  - hc_eng in the centre void, the inner hc_<q> client and the 4-beat x_wave;
  - the hub W-face pin spread with the calendar window, and lane legs;
  - the hb_ckgen slot as on main (267.84 × 220.32 at 17426.8, 13431.554).

## Measured (`eval.json`, slack 1200, `--spread ... --lanes-mode legs`)
- **Cuts:** {'worst_v': {'ratio': 0.535, 'x': 13700.0, 'y': [5200.0, 6200.0]}, 'worst_h': {'ratio': 0.577, 'y': 18500.0, 'x': [13600.0, 14600.0]}, 'lines_over_060': 0, 'windows_over_060': 0} 9.364. 0 lines over 0.60.
- **Band barrier through su_<q>1** (839.2 µm free over and under the slices; rp4c roof 270.72 µm):

| Traffic | Without roof | With roof |
|---|---|---|
| SFU/SU only | 0.227 | 0.171 |
| Including HC, 4,900 b | **0.415, passes** | 0.314 |

  It now passes without the roof.
- **RF relays:** 16 routes, 35 stages required against the production 36. 576/576 footprints placed, max hop 475 µm.
  The margin is thin: 1 stage.
- **HC_ENG:** at most 15 stages per direction (`hc_eng_home.json`).
- **XC witness at rp4c** for this plan: `../xc_rp4c_frame_b3624`.
- **Images inspected:** `layout/die_floorplan.png` and `layout_sw_band/die_floorplan.png`. No overlaps.

## Pending
- **SUCX conflict:** the source-compact 720 × 720 SUCX would conflict with hc_<q> by 54 µm, as in v4.
- Everything still open from v4.

## Reproduce
```sh
N=results/arch/hbm_die_v15/core4_sfu2_b3624
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3624.48 --su-w 1797.12 --su-h 2825.28 --smw 7200 --smh 1800 --edge 100 --column 3050 --channel 450 --hub-w 480 --fit --carry --sfucore-h 3580 --sfu-store-side --sfus-wh 1020 1412 --sfus-yoff 2190.88 --hc-eng-mm2 9.5 --hc-links-v16 --hc-x-beats 4 --hc-client-inner --out $N
python3 tools/hbm_die_v15/v6_eval.py $N --slack 1200 --spread vmh_SW:W:159.84 vmh_NW:W:159.84 vmh_SE:W vmh_NE:W --lanes-mode legs
python3 tools/hbm_die_v15/xc_rp4b_frame_witness_1016.py --tile rp4c --ref e15f1ee76 --candidates core4_sfu2_b3624 --out results/arch/hbm_die_v15/xc_rp4c_frame_b3624
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $N [--borrow-roof --roof-witness results/arch/hbm_die_v15/xc_rp4c_frame_b3624/witness.json] [--graph-cls HC_ENG HC_CORE] --out ...
python3 tools/hbm_die_v15/rf_centre_routes.py $N && python3 tools/hbm_die_v15/rf_centre_allocate.py $N
python3 tools/hbm_die_v15/rehome_v6.py --plan $N --old results/arch/hbm_die_v15/core4_sfu2_su2825 --adopted "..."   # adopted into hbm_v15.json
```
