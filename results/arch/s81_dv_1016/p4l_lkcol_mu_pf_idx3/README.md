# S81-DIEPLACE2 (10-20): p4l-MU die plan with grown L20 reader slots + gunit L5 fit (for GEN mu6)

Plan `plan.json` = `dv_plan.py --layout p4 --tier-w 276 --lanes 4 --p4l --p4h-drop 6 --frame-w 1436.832 --mu 1 --pathfix
--lk-slots results/arch/s81_dv_1016/p4l_lkcol/plan.json --revision dv-p4l-mu1-idx3 --idxrd 3`. `--idxrd 0` (default) stays
byte-identical to current main's output (checked). Flow PNG `dv_flow.png` (viewed).

## Why the old slot cannot grow in place (idx_fit.json)
The ENG=1 reader holds 0.684 mm2 of hard macro (32 hslices as 4 columns 691.2 x 829.44 + 9 x 1024x256 SRAM); it needs about
0.9-1.0 mm2. In-line on its region rq/rd, the reader gets at most 518.4 x 777.6 (0.403 mm2) at the 531.25-um region pitch:
the service band must stay under s_3S / s_4S, where the q / P.V entries rsv_05 / rsv_11 land, and the die height is fixed by
the reticle. The other placements (beside or above the band, the PHY corners, two rows, or a split engine) either break the
abutted svc_rs faces or put 4-8 x 1,244 b laterally into a 220-um channel.

## Chosen: --idxrd 3 (wider pitch: one reader per controller pair)
- 8 readers `irg_00..07`, master **dsdv_idx_rg2** (2-region reader: rqi0/1, rqo0/1, rdi0/1, rdo0/1, one ENG=1 engine),
  1,036.8 x 1,036.8 (24 x 43.2 square, 1.075 mm2; 0.537 mm2 a region) at a 1,062.5 pitch, abutted 40 um above the controller row (y 1,490).
  Slot fits 4 hslice columns + a 174.7-um SRAM column + halos (~996 um) by 829.44 + std band.
- The service band moves up into the column-2 / column-5 voids (x 9,819-22,150, y 2,746.8-4,986.8). Each svc_rs slice is 1,431 x 1,100
  (1.574 mm2, fit 1.056 against the 1.491 estimate; p4l was 1.124). The tree, entries rsv_05/rsv_11, roots 07/09, and all face lanes and gaps are unchanged.
- The 6 row-1 frames over the band are dropped (f_2R01, f_3L01, f_3R01, f_4L01, f_4R01, f_5L01). This costs the same as the idxrg2 slot did.
- New units and lanes: qf (259.2 x 432, W of reader 0), query chain 2 x 276 and score chain 276 between abutted readers (25.7 um, 0 stations),
  iq_src s_3S->qf 2 x 276 (21 stations), and is_tail irg_07->bk_sel 276 (36 stations). mu_0S / mu_7S are re-routed past the band ends.

| | p4l_lkcol_mu_pf (main) | idx3 | delta |
|---|---|---|---|
| ROM slots | 1,130 | 1,070 | -60 (-5.3 %, about +5.6 % S81 dies at the same model) |
| die | 31.97 x 25.00 = 799.2 mm2 | same | reticle-bound |
| reader silicon | 16 x 0.403 = 6.45 mm2 (idxrg2 plan) | 8 x 1.075 = 8.60 mm2 | +2.15 mm2 |
| worst cut | 0.5663 | 0.5663 | 0 |
| over-reach bits / lanes over blocks | 0 / 0 | 0 / 0 | |
| relays | 3,113 | 3,148 | +35 |
| relay bit-stages | 843,266 | 856,764 | +13,498 (+1.6 %) |
| bit-mm | 395,382 | 400,886 | +5,504 (+1.4 %) |
| lane band over block | 32.2 bit-mm / 74 relay overlaps | 0 / 78 | |

Stage changes, to be priced into the schedule and the landing plan (land_plan p4l3 ages are stale for these lanes):
- HBM rq/rd: at most +1 station per direction (regions 0,1,2,10,12,14,15: +1; region 11: -1), plus the reader's own in-line pipeline.
- q_W/q_E/pv_W/pv_E: 2 -> 0 stations; jw_E/jd_E: 24 -> 22; jw_W: 33 -> 31; jd_W: 32 -> 31; mu_7S: 69 -> 68.
- index chains: the 15 neighbour hops become 7 (8 readers). iq_src is 21 stations and is_tail is 36.

Open issues and RTL owed (not done here):
- **dsdv_idx_rg2** (S81-L20RD): one ENG=1 engine serves 2 regions. Steady load is 2 x (1 key / 3 cycles) against an engine
  capacity of 1 key/cycle, so headroom drops from 3x to 1.5x. Measure it on a production-shape 2-region bench with the x_t0 sweep before adoption.
- svc_rs E/W face pin density is 8,999 b / 1,100 um = 8.2 pins/um (p4l 6.7/um, both above the 6/um rule). N/S faces improve to 5.4 (from 6.2).
  The svc_rs kit (owed, S81.BIND.SM.1) must spread its pins over two layers or rebalance its faces.
- White space: the dropped row-1 footprints above the band (about 2.35 mm x 3 pairs) hold no block. Only the band-top lanes cross them; a 2,349-um strip cannot hold an H9 frame.
- Bind: `plan_bindvar_mu5src.json` = the idx3 plan with readers bypassed (no dsdv_idx_rg2 RTL yet) and without the main-only pr_09_07 lane,
  bound with the GEN mu5 source 804d68ef6 (results in the lane file / below).

## gunit (gunit_parent_pack.json)
The closed dsdv_gunit_l5 (route dsdv_gunit_l5_ro3-ro3-648ee10c0, 388.8 x 302.4) and the other 8 leaves (0.568 mm2) fit the
existing 680 x 4,035 die reservation on the 43.2 lattice with 86.4-um channels (fill 0.21). The 259.2 figure was the Q4 model's
leaf baseline, not a die slot, so there is no die block, lane or station change. Parent hardening still owes the internal rung relays (or a shrink to about 680 x 2,074).
