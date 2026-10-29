# QC-A0-KITS-13 (2026-10-29): NL ICG0 re-place, NK floorplan V1/V2 estimate, clock-gate enable estimate

Base: origin/main 7a77f0bc6. Run dirs: intel2 and intel1 `/srv/opentallas-scratch2/claude/qc-a0-kits-13-1029`.
Inputs: the NK v2 placement from QC-A0-KITS-12 (`nk_geom/geom.tsv`) and the NL reset6 placement
(intel1 `codex-qc-a0-2340/parent_reset/.../3_place.odb`; geom_dump.tcl was re-run on it, giving `nl_r6_geom/geom.tsv`).
Scripts are in this directory (`region_stats.py`, `badpaths2.py`, `where.py`, `node_conn.py`, `hcut.py`, `render_v1.py`).
CHECKED = measured from those dumps by these scripts. UNCHECKED = analytic.

## 1. NL ICG0 typed placement (COORD ruling b)
- I stopped Codex unit `oth-ubuntu-582810-1793274530` at 06:40 PDT, and only that unit: container 38f3b8af35bc, at iteration 23650.
  At the stop, overflow was 0.434, HPWL 2.72e7 and penalty 3.8e29.
  Its log is kept here as `nl_icg0_3_3_fail1_diverge_16t.log.gz`. Codex's kit dir is untouched; I made the copy below.
- Settings difference from reset6 (CHECKED): the config.mk GPL arguments are identical: `-density 0.45 -routability_driven -timing_driven
  -force_center_initial_place -min_phi_coef 0.95 -max_phi_coef 1.05`, with the divergence revert ON by default.
  The only difference is the thread count. reset6 ran with `--cpus=8 NUM_CORES=8` (`run_parent_reset_place.sh`); fail1 ran with 16.
- ONE rerun with the reset6 settings (`nl_icg0_place_r6.sh`): a copy of the kit, restarted at 3_3, 8 threads.
  It runs on intel2 as ot-heavy unit oth-ubuntu-3473313-1793281925, container qca0k13-nl-icg0-place-r6.
- RESULT (CHECKED, `nl_icg0_3_3_r6_8t_stopped.log.gz` vs fail1): the run is bit-identical to fail1 at every compared iteration.
  The iteration table matches to all printed digits at 3330 (0.4448 / 1.816879e6), 4710 (routability end, 0.6312), 4830 (min overflow 0.2043 / 1.849935e6),
  4910 (0.3518 / 7.276978e6) and 4920 (0.4010 / 9.525529e6). GPL is deterministic, so the thread count is not the cause.
  I stopped my own container at iteration 5070 (HPWL 2.35e7, same divergence). That counts as the ONE rerun.
- Diagnosis (CHECKED from both logs):
  - reset6 timeline: routability ends at 3330, overflow falls to 0.152 at 3470, and timing-driven iteration 2/2 runs.
    Its +19.9% HPWL step trips GPL-0323/0998, which reverts to iteration 3441 (overflow 0.191, HPWL 1.77e6).
  - ICG0 timeline: overflow bottoms out at 0.2043 (4830) and never reaches the TD-2 trigger point. So TD 2/2 never runs and the
    divergence check never arms. HPWL then climbs 1.85e6 -> 2.7e7 while overflow stays at ~0.45.
- Proposed (ASK, DEFAULT if no answer in 30 min): one run with `GLOBAL_PLACEMENT_ARGS=-overflow 0.21`, with everything else reset6/fail1-identical.
  GPL then stops at its own minimum-overflow point (0.2043 at it. 4830, HPWL 1.85e6, before the blow-up).
  That end state matches what reset6 reached through its revert (overflow 0.191). Global placement only; DPL/AUTO-GEOM then decide.

## 2. NK floorplan: V1 (move the node) and V2 (re-space the rawfault columns). ESTIMATE ONLY, no build.
### What actually fails in the NK v2 placement (CHECKED)
- Std-cell area is NOT the limit. Std-cell utilisation of free area in the upper half (y >= 658) is 7.0% in NK and 4.7% in NL.
  In NL, the east column (x >= 388, y >= 669.6) holds 10,926 cells (3,333 FF) and 1,566 um2 of std-cell area in 31,740 um2.
  That is 4.9% utilisation. The free rawfault slot (142.2-257.5 x 673.9-814.3, 16,195 um2) is only 3.8% used in NK.
  KITS-12's "too little std-cell space" diagnosis is therefore wrong on area.
- The 124 captures beyond 405 um (`nk_v2_bad_paths.json`) fall into two groups:
  - 8 are ICG enable paths: n_b_q[513] at (5, 901) on the W face -> g_icg.dr[0..7] at (406, 668). Distance 630-635 um. This is section 3.
  - 116 are u_me stage FFs going to u_tx relays: u_me.s2_x / s2_tag / s2_first / s2_gm FFs -> g_hier.g_sl[k].g_tx u_tx q, up to 570 um.
    In NL the s2 stage sits in the east column, at x 366-410 and y 669-905 (median 820). In NK the node took that column,
    so GPL pushed the s2 stage below the node, to y 664-674 (median 669). From there it is up to 570 um from the u_tx relays at (108-136, 980).
- The NK channel_v of 1.845 and col_v of 1.696 sit at x 196-206 / 260, y 522-527. That is the lower central street, which NL reset6
  already flags (1.50 / 1.82). It does not come from the node.
- The structural cause is the node pin faces (from the LEF, CHECKED):
  - Node W face: 2,051 pins: a, b, y, t_out (512 each), plus va, vy and t_vout.
  - Node E face: 515 pins: t_d (512), fault, rst_n and t_vd. The node clk pin is in the interior.
  - In NK, all four W-face buses connect to tile W-face pins at x = 0: n_a (y 699.6-800.6), n_b (800.7-900.8), t_out (901.0-1001.2)
    and n_y (1001.4-1102.6). n_a/n_b are inputs; t_out and n_y are outputs.
  - With the node in the east column, 2,056 bits must cross the upper half from x 0 to x 394.
  - Upper-half horizontal crossings per vertical cut (hcut.py, nets with 40 or fewer terminals):
    - NK: 3,378-4,682.
    - NL reset6: 594-2,275, measured at cuts x = 60...385. In NL only t_out crosses.
  - The bit-level reach of the node bus is hidden from the r2r metric, because the node is a macro.
    Example path: pin reg n_a_q at (5, 700) -> node a pin at (394, up to 1099). That is <= 389 + 400 = ~690 um,
    above the 405-um reach (UNCHECKED: geometric bound only, not STA).
### V1: node to the W edge (DEFAULT from DIE-QC-30; legal site found)
- Site: node at (20.52, 688.656) in R0 orientation. That leaves an 11.9-um pin-register strip at x 4.32-16.2 for the 1,028 n_a_q/n_b_q FFs.
  The W-strip utilisation is 14% now in NK (CHECKED), and similar after the move (UNCHECKED).
- The 8 rawfault macros shift +60.70 um in x and keep their rows. The columns land at x 76.68 / 202.82 / 328.97, with the same 10.8-um gaps.
  The last column ends at 444.31, inside the core edge minus halo (449.28). The east strip becomes 9.3 um.
  The free slot moves to 202.8-318.2 x 673.9-814.3. That puts it above the central street and the clock entry at (229, 579).
  The romleaf columns, the clock entry and the E-face pins do not change. PLAN PNG VIEWED: `nk_v1_v2_plan.png`.
- Area: std-cell area is unchanged. The ~1,566 um2 of NL east-column logic (the u_me s2/s3/e_first root stage) gets the free slot.
  Utilisation there becomes about 13%. Upper-half utilisation stays at about 7% (UNCHECKED).
- Reach (UNCHECKED, geometric):
  - Node t_out <-> tile t_out: about 20 um. These pins are already y-matched: node t_out spans 900.6-999.9 and tile t_out spans 901-1001.
  - n_a / n_b / n_y: the node interleaves a, b and y over its full 400-um height (y 699.6-1111.5), but the tile groups them in 100-um bands.
    In V1 that leaves a vertical run of up to ~300 um (average ~150) along the W strip. This replaces the current ~390 um horizontal run plus the same vertical run (<= ~690).
  - t_d (ME root -> node E face at x 68) replaces NL's t_out run (ME root -> W pins at x 5), which is 63 um longer.
    NL closed r2r at 404.35, so t_d is expected <= ~405.
  - The 116 u_me s2 -> u_tx paths: the root stage goes back to a site near the u_tx centroid (x 162, y 840).
    Expect NL-like reach of <= 404 um, the NL reset6 result.
- Channels (UNCHECKED, counted from hcut):
  - Upper-half H crossings fall by about 2,000 per cut (1,542 W-face bits for n_a/n_b/n_y no longer cross).
    t_out is replaced by t_d, so the cut count returns to the NL range of 594-2,275, against 6,500+ M6 over-macro tracks
    plus 2 x 20-um row gaps (~9,100 tracks raw, ~5,460 at 0.6).
  - New local demand: up to ~1,000 vertical bits beside the node, in the W strip plus M7 over the node.
    About 16 um x ~48 tracks/um plus 47.5 um x 15.6 M7 gives ~1,500 tracks. Expected utilisation ~0.65-0.7: watch item, GRT decides.
  - A die pin-plan option removes this watch item: order the tile W pins n_a/n_b/n_y per bit, the way the node does.
    Then the vertical runs are about 0 um. This is a QC die pin-plan change, so DIE-QC-31 owns it.
### V2: re-space the rawfault columns to open a register column (node stays east)
- Width check (CHECKED arithmetic): 3 x 115.344 + node 47.52 + halos/gaps (4 x 8.64 + 2 x 4.32) = 428.1 um, out of 449.28 usable.
  At most 21.2 um can open; packing the columns west opens 13.9 um at x 376.3-390.2.
  A 60-um FF column cannot fit while the node keeps the east column.
- V2 keeps all 2,056 node-bus bits crossing the tile: H cuts stay at 3,400-4,700, and the ~690-um node-bus reach remains.
  So V2 helps only the 116 s2 paths, and only partly.
- VERDICT: V1 is better on every number. V2 is not recommended. V1 is a QC PLAN change (DIE-QC-31) and needs GEOM REQ before any build.
  Build order after the pick: slice/recipe -> GEN -> one placement -> AUTO-GEOM with GRT.

## 3. Clock-gate enable path (COORD ruling d): estimates for both forms
Logic (qfd_tile_nk_a0c.sv g_icg; NL is the same without nv):
- One tile-root ICGx8DC gates the whole body.
- en = !rst_n | go_f | go_h | !me_idle | nv_f | (dr != 0), with a 1-cycle lead.
- Sources: nv_f is merged into the n_a/n_b pin registers (W face, y 700-901). go_f is the tap[0] pin register (E face, y 561-660).
  rst_n is on the E face (y 670). me_idle comes from the u_me root.
Basis:
- Measured: the NL native CTS put the ICG CK at 42.78 ps and the leaf at ~796 ps. Plan core IO reference: 692.6 TT.
- Assumed (UNCHECKED): wire at ~1.0 ps/um repeated, from the 600-750 um per cycle of measured repeated reach.
  60 ps uncertainty, ~20 ps ICG setup, ~45 ps clk->q, ~40 ps OR logic.
- Today (ICG at the root): the budget is 833 - (692.6 - 42.8) - 20 - 60 = ~103 ps for clk->q + OR + wire.
  The NL measured value is -610.26 ps, caused by the insertion-delay difference alone.
  NK adds 634 um of wire on top (n_b_q[513] -> dr): about -1.2 ns (UNCHECKED).
- Form A (enable launched next to the gate on the root clock): the en -> ENA path becomes local (about +600 ps).
  But every source -> enable-register path then launches on the leaf clock (~693-796 ps) and captures on the root (43 ps).
  The same -650..-750 ps penalty moves there before any wire. For nv in NK, add ~634 um: about -0.6..-1.3 ns. Form A only moves the failure. REJECTED.
- Form B (gate replicated per cluster, ICG at leaf level): the ICG CK lags the leaf by only the local stage (~80 ps, UNCHECKED).
  The en budget is then 833 - 60 - 20 - 45 - 40 - 80 = ~588 ps, about 590 um of wire.
  - B with one shared en for the whole tile: worst source -> replica distance is nv (5, 901) -> (458, 0) = 1,354 um, or tap -> (0, 1158) = ~1,050 um.
    Both exceed 590 um by 2x. FAIL.
  - B-hop (recommended), the locality-first form (12.13): each replica gates one cluster. Its enable rides the data hop chain:
    the enable is relayed with the same registered hops as the data it gates. A cluster h hops from its activity source
    receives data no earlier than h cycles after the source, so the enable can use the same h hops and the 1-cycle lead holds.
    The first gated capture next to each source stays local:
    - go_q is next to the tap pin registers on the E face.
    - In V1, the node and its face logic are next to the n_a/n_b registers on the W face.
    Each enable hop is <= 405 um by construction, the same plan reach as data.
  - Cost: one ICGx8DC per cluster plus h relay FFs per cluster enable (~a few hundred FFs, UNCHECKED).
    Clusters are taken from the existing hop structure: node, E-face IREG, per-g_sl tx groups, rawleaf and romleaf columns.
  - Gating changes per cluster, so the build needs the existing Codex ICG operational miter:
    valid/fault/data-when-valid must match exactly, and inactive data differences stay transparent.
- RTL owner/merge: rtl/qfd_tile_{nl,nk}_a0c.sv is shared rtl, so a B-hop RTL change waits for a ROOT-MERGE approval.
  Build plan: RTL on a claude/ branch -> SYNTH/SELRANGE/FACE -> native LEC + ICG operational miter -> one placement each in NL and NK
  (NK on the V1 plan). See the ASK in COORD-REVIEW-QUEUE.

## 4. Collected / live
- NK GRT probe from KITS-12: intel2 container ap-ageom-qca0k12nk-grt-1852076 is at iteration 8/50 (06:33), at ~3 min per iteration.
  It finishes ~08:40 PDT; files: `qc-a0-kits-12-1029/nk_geom/{grt.log,cong.rpt,auto_geom.json,auto_geom.png}`.
  The probe is diagnostic only: the NK v2 placement is already GEOM FAIL and the plan is changing to V1.
  The intel2 worktree wt/qc-a0-kits-12 has to stay until the probe ends, because geom_rules runs from it.
