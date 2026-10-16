# core4_sfu2_b3624: v5 plan (measured SFU core, rp4c SM carve frame)

**ADOPTED** into `results/arch/hier_contract_1015/hbm_v15.json` (version 8) by H-DIE-V790 on 10-16, on the H-DIE
decision and the addendum. The rehome ran from the v4 homes (`--old ../core4_sfu2_su2825`). Audit: 0 slots outside the
die, 0 overlaps, 0 points in hard blocks.

## What changed from v4
- **SFU core:** `sfucore_<q>` is 763.56 × 3,580 (H-SU: the cluster-legal lane view is 216 wide, 3 per row).
- **Band:** 3,624.48 (+471.2).
- **SFU store:** `sfus_<q>` stays 1,020 × 1,412, at y offset 2,190.88. It is 21.6 µm below the band top, above the
  group-2 hc/sfu leaves.
- **SM slot:** the H-SM rp4c frame with the OWNER feedthrough carve, **7,228.80 × 1,807.20**.
  - Reserved channels: a W-edge column at x [0, 40.32] and an N-edge row at y [1,766.88, 1,807.2]. These are recorded as
    the SM slots' `reserved_channels`.
  - `rtl_pin_grants_1405.py` has new `SM_CARVE` / `ft_forbid_sm` / `ft_record_sm` for these; the centred v15
    column/row stays the default.
  - All content shifts +40.32 in x. The die SM pin windows on N/S faces shift +40.32 (`v6_eval.py --sm-carve 40.32`).
    No pin sits in a carve foot: N/S offsets are ≥ 50.32, E/W offsets ≤ h − 50.32. 0 violations in the contract.
- **Die width:** the four wider SMs add 115.2 µm. This was recovered with the die edge margin, 100 → **42.4**, so the
  width stays 32,990. Trimming the two 450 channels to 392.4 was also measured: the cut is worse (0.548/0.597 against
  0.529/0.528), so the channels stay at 450.
- **Die:** 32,990 × 25,165.202 µm = **830.2 mm²** (+33 mm² over v4).
- **XC home:** x 3,828.96, y 1,550.88. Its witness is `../xc_rp4c_frame_b3624` (`--tile rp4c --ref e15f1ee76 --carve
  40.32`).
  - The roof is now y 1,529.28–1,766.88, 237.6 µm high.
  - Over the XC (0) and the front (1.44) it is 0.
  - Conditional free roof area: 1.578 mm² per SM.
- **Unchanged from v4:**
  - hc_eng in the centre void, the inner hc_<q> client and the 4-beat x_wave;
  - the hub W-face pin spread with the calendar window, and lane legs;
  - hb_ckgen as on main (267.84 × 220.32 at 17426.8, 13431.554).

## Measured
- **Cuts** (`eval.json`, slack 1200, `--spread ... --lanes-mode legs --sm-carve 40.32`): **V 0.529 / H 0.528, 0
  lines over 0.60.** Weighted stages 9.376.
- **Band barrier through su_<q>1** (839.2 µm free over and under the slices):

| Traffic | Without roof | With roof (237.6 µm, 1,076.8 µm total) |
|---|---|---|
| SFU/SU only | 0.227 | 0.177 |
| Including HC, 4,900 b | **0.415, passes** | 0.324 |

- **RF relays:** 35 stages required against the production 36. 576/576 footprints placed, max hop 463 µm.
- **HC_ENG:** at most 15 stages per direction.
- **SM_HBM** (`sm_hbm_hops.json`, 480 µm reach, relays outside hard blocks):
  - 79 of 234 hops are over 600 µm, max 4.34 mm.
  - With relays allowed inside the SM frames, 20 remain, max 3.59 mm. All of these cross the band (sfucore/SU), not
    an SM.
  - See `../sm_hbm_hops_1016`.
- **Images inspected:** `layout/die_floorplan.png`, `layout_sm_corner/die_floorplan.png` and
  `layout_sw_band/die_floorplan.png`. No overlaps.

## Open
- **SM HBM port face.** The H-SM frame has its SM_HBM window on N (offset 5,307.52, crossing the N carve row on M5). The
  die grant, top-down from the plan, puts `packet[1098:0]` on the PC-facing face: S for the S quadrants at offset
  1,917.52, N for the N quadrants. One of two things must happen:
  - the S-quadrant frames are placed MX, which moves their carve row and XC to the S edge; or
  - the H-SM kit adopts the die faces.

  This is an H-SM/H-DIE decision.
- **SUCX conflict:** the source-compact 720 × 720 SUCX would conflict with hc_<q> by 54 µm. This is pending
  H-NETLIST/H-SU adoption.
- Everything still open from v4.

## Reproduce
```sh
N=results/arch/hbm_die_v15/core4_sfu2_b3624
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3624.48 --su-w 1797.12 --su-h 2825.28 --smw 7228.8 --smh 1807.2 --column 3050 --hub-w 480 --fit --carry --sfucore-h 3580 --sfu-store-side --sfus-wh 1020 1412 --sfus-yoff 2190.88 --hc-eng-mm2 9.5 --hc-links-v16 --hc-x-beats 4 --hc-client-inner --channel 450 --edge 42.4 --out $N
python3 tools/hbm_die_v15/v6_eval.py $N --slack 1200 --spread vmh_SW:W:159.84 vmh_NW:W:159.84 vmh_SE:W vmh_NE:W --lanes-mode legs --sm-carve 40.32
python3 tools/hbm_die_v15/xc_rp4b_frame_witness_1016.py --tile rp4c --ref e15f1ee76 --carve 40.32 --candidates core4_sfu2_b3624 --out results/arch/hbm_die_v15/xc_rp4c_frame_b3624
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $N [--borrow-roof --roof-witness results/arch/hbm_die_v15/xc_rp4c_frame_b3624/witness.json] [--graph-cls HC_ENG HC_CORE] --out ...
python3 tools/hbm_die_v15/rf_centre_routes.py $N && python3 tools/hbm_die_v15/rf_centre_allocate.py $N
git show 8f97fc778:results/arch/hier_contract_1015/hbm_v15.json > results/arch/hier_contract_1015/hbm_v15.json   # v4-homed contract
python3 tools/hbm_die_v15/rehome_v6.py --plan $N --old results/arch/hbm_die_v15/core4_sfu2_su2825 --sm-carve 40.32 --adopted "..."
```
