# HEAD hd_ctl outline: estimate before build (DIE-HEAD-25, 2026-10-29)

ESTIMATE ONLY (12.14b). No P&R. Plan: hk4 `results/die_head_21_1028/hk4/plan_spine_raw_rx_tx.json.gz`.
Numbers are my own (scripts here), UNCHECKED by NUMBER-CHECK.

Inputs. Std cells 17,214 um2 and 4 SRAM `ot_sram_1r1w_64x512_m1_r2c2` (171.288 x 77.784, 53,294 um2). Source: HEAD-KITS-7 hk4 kit synth
`intel2 head-kits-7/ctl/kits/hd_ctl/run/reports/asap7/dp_hd_ctl/base/synth_stat.txt` (chip area 70,508 incl. SRAM).
Face bits from the plan: W 3,324 (lepk i/o 2x1104, ft w3u/w3d out/in 1026, ctl 90), S 1,939, N 1,026 (ft only), E 128.

1. **216 x 233.28 is INFEASIBLE for hd_ctl.** That number is Codex's HBM CTLX (`ot_hgi_sm_xload_cl2_ctlx`, commit 09ccb3d869,
   std 10.65k + SRAM 3.89k). hd_ctl is a different block. 216 x 233.28 = 50,388 um2, which is smaller than its 4 SRAMs alone (53,294).
   Its W face would also need >= 3,324 / 12 = 277 um of pins at the 6 pins/um/layer x 2 layers budget.
2. **The current slot 1442.88 x 1226.88 is pin- and abutment-sized.** Total fill is 4.0% and std fill of free area is 1.0%. All 21 ctl
   links abut their neighbour (sp0 S, lep0N W, nst7 E, lk_WN3 N via the w3 ft) at L1 = 0 um (`ctl_links.txt`). The windows run to
   y 1124.7 (W) and x 1282.9 (N ft), so no crop that keeps the pins buys area.
3. **Smallest feasible outline (plan-fix variant B1).** Every bus and ft slot stays on its face. Pins are repacked at the budget,
   and the SRAMs go 2x2 or 1x4.
   - B1, 6 pins/um/layer: **362.88 x 371.52**. Total fill 52.3%, std free fill 21.1%, macro 39.5%.
   - B1r, 5 pins/um/layer (slack): **362.88 x 423.36**. Total fill 45.9%, std free fill 17.2%.
   Both pass the GEOM fill band (>= 0.15).
4. **Cost of B1.** It is a spine-root re-plan, not a type-local change.
   - Gap left by the shrink: ~1080 um to the E neighbour nst7 (m7N tx/rx, 64+64 bits) and ~855 um to the N neighbour lk_WN3 (w3 coll ft, 1026 bits).
   - The m7N link needs >= 3 hops at 405 um. Count-aligned stations add cycles, which the static schedule absorbs (12.15c).
   - The w3 ft (5 stations today) must re-route.
   - Windows move on lep0N's E face (type hd_lep0N, still NEEDS-KIT) and on sp0's N face (type hd_spn is shared by sp0..sp5, so it needs a
     variant or a common window move).
   - The event resets the hk4 GRT0, clock, CA and START work.
5. **Less disruptive variant B2: hk4 strip form.** Crop hd_ctl to B1 at the SW corner. The rest of the old slot becomes 1-2
   feedthrough strip types, the same mechanism as the hk4 strip outlines. They carry the old outer-face windows to the cropped ctl, so
   no neighbour pin moves. Cost: 1-2 new strip types and their stations (cycles priced); the ctl internal path lengths shrink.
   Recommended over B1.
