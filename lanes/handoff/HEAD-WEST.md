# HEAD-WEST handoff (split from HEAD-R18, 11-23 19:2x PST)
Job: pick HEAD West form at GRT; nst4 kit if (b) wins; else next structural form. Every chain: --remap-base = parent plan (LANDREMAP fail-closed).
- Kits (intel2 ~/fable-fix-head-lep0n-1122/r18g_exact_continue/west-*; kit dirs epyc7 .../head_rp21z20NF15f_r17b/private/HEAD-R18/):
  - (a) wband prep_r18g_wband 014661a6ea33: hd_lep0N_w_1123175932 (unit head-r18-west-wband-grt)
  - (b) wch4b prep_r18g_wch4b f570eb1144eb: hd_lep0N_w_1123175934 (unit head-r18-west-wch4b-grt)
- Waiter: head-r18-kit-waiter5 (waiter3/head_waiter.sh) posts raw reads as HEAD-R18 + WEST WINNER + launches west-wch4b-nst4/run.sh if (b) first at 0.
- 19:2x: wband tap-pre GRT 0 overflow (12 extra its); wch4b still iterating.
- Local watcher: scratchpad west_watch.sh (background).
## 20:3x PST: WEST WINNER = (a) wband
- hd_lep0N_w_1123175932 5_1_grt: 0 overflow on clock (3,235 nets) + signal (134,451); TT setup ws +63.2 tns 0; FF hold guard +27.7, 0 violators (+201 buf). Render grt/congestion.png: red only over the hard cores; channels green/yellow, no hotspot at the old x60-110/y840-960 corner.
- No nst4 (only for (b)). wch4b hd_lep0N_w_1123175934 keeps running as a spare (in pre-GRT hold at 20:32).
- Unit head-west-wband-route (west-wband-route/run.sh): waits for the head-r18-west-wband-grt driver to end, then run-item same spec --goal route (sign-off+LEC), OT_LANE=HEAD-WEST.
- Waiter head-west-waiter (waiter_west/) still posts the raw reads for both kits.
## 20:4x PST
- COORD accepted wband. Required before it counts: classify the 5_1_grt.json hold -132.6 / skew 598 on the final stage db after sign-off; internal FF hold must be >= 0, and anything negative must be forwarded ring inputs only, within -568. Post the endpoint split + send the route render to FABLE-RC-ALL.
- waiter_west had an ls short-circuit bug (failed.odb* absent -> rc 2): fixed, now head-west-waiter2. Told HEAD-R18 its waiters carry the same line.
- head-west-wband-signoff-wait (waiter_wband_signoff/) posts the raw sign-off read + hold lines + render paths when head-west-wband-route ends. The lane still has to classify.
- Preview: pre-GRT FF OT_HOLD_GATE -86.4 (4205 ep, 1554 forwarded ring inputs, limit -568.4); post-repair FF hold guard +27.7, 0 violators; json -132.6 was read under TT vclk binding (likely IO/ring), unclassified.
## 23:5x PST: wband run 1 NOT signed off; next kit = 4 rows (FABLE f2876120). NOTHING BUILT OR LAUNCHED YET
- route2: refused at chain_admit 23:30 (kit already routed), no result. Kit hd_lep0N_w_1123175932 is terminal. A fresh private kit is needed, with a bind of the exact new plan and --remap-base = parent plan 014661a6ea33.
- My hand-written count_strap_evidence.json was reverted (generated copy restored; the pre_headwest copy is identical). Do not repeat it. Row 4 belongs to KIT-STRAP-EVIDENCE; fallback is declaring 18 tied straps in the plan. No landing seen on the hub at 23:5x.
- Row 1 (DRC 2): M7 VSS strap centre x 444.768 (444.624-444.912) over k_li_d[527] (444.688-444.720), strap end 846.616 / 509.864 vs core face 846.72 / 509.76, gap 0.104. CLASS: 126 pin/strap pairs on the two cores match x gap < 0.05, end gap < 0.5 (script scratchpad alias.py, printed ones all 0.104); only [527] failed in DRT. Fix the end gap at the core faces for all of them, not one strap. Who sets 0.104 is NOT found (core edge trim is in pdngen/halo, not proved to be reserved_pg_cut.tcl).
- Row 2 (-56.3): fs_q -> INVx1 (12 loads, slew 206) -> AND3x1 (slew 185) -> AND2x2 -> 3 buffers -> sl[2].ch[0].u_wen, total 762 ps after launch. Small gates with bad slews plus the 320 um band, not just fs_q fanout. GRT read +63. No plan knob found for fs_q copies (fs_q only in rtl/common/ot_dp_clk_landing_ca.sv:452-463, shared by all dies; would be a default-off parameter + LEC). Not yet inspected: -54.2 lap_ok, -47.6 tx SRAM odr.
- Row 3 (-15.8): u_rg1.u_pair -> u_rg1.g_rxf.g_s[0].u_st.q[117], 1 end. tap_pair_affinity {macro_follow: true} is ALREADY in this plan, so that knob did not cover it. core_taps early, core_tap_lead_ps 210. Cause not found.
- Units live: only head-west-wband-progress2 (exits by itself, posts nothing). No West build is running.
## 11-24 00:1x: sign-off STA on run 1 (analysis only, epyc7 head-west/sta_run1): NOT SIGNED
- TT setup -56.35 (u_rg2.u_pair/k_lo_v = group 4, told HEAD-W-SETUP), FF internal hold -34.87 (39 ends: 36 u_rg1 pair outputs, 35 on clk_t52; 3 u_rg2 TX slice), DRC 2, face_guard 3, drv slew. LEC not run.
- Port hold 3643 negative, worst arst_n -93.51 / start_i -92.96: NOT only ring inputs; none below -568.4.
- Row 3 choice pending: c0 ~40 ps later vs launch-side lockup (TT room +348.9). Do NOT move capture to the pair tap (~690 ps apart). Need FF c0/c1/t52 arrivals + positive pair-input hold margin.
- Straps: bound top = tie audit for lep0N_w (001100/010000/010000). ba24d0117180 misses 18/18; KIT-STRAP redo ~01:15 from the bind tie audit, else fallback in plan at 02:30 checked against the NEW bind.
- Deltas awaited: HEAD-W-DRC, HEAD-W-SETUP. Launch ETA re-post due 02:30. Nothing launched.

## CODEX notes 11-24 06:3x PST
- w5 1e8ebd1417ab on epyc9. Initial native release/G0 failure fixed by the inherited fwd requal step, both rc0. Initial Yosys harness incorrectly expanded the match list and produced invalid observation-cut results. Actual 16-edge receiver-output lockstep passes self and independent two-stage reference, and detects zero stage, one stage and one flipped receiver bit. E9 oth-ubuntu-1758474-1795530842, head-west/lec_w5/lockstep_reduce_0635, exit0.
- Exact corrected dchn FF library from main b335c934 is staged (8bc587a4f5b9, matching TT e240e3b28304). On the prior signed parent, corrected FF gives -48.79 ps and 93 internal endpoints from u_phy.u_link.u_dec.u_chn/cw_q to g_oreg.r_cw. Incoming K-to-core hold remains +102.23 ps. Two stations handle the priced coll_i0 bank, and the distinct dchn-to-capture hold must be measured on w5. Prepared head-west run_w5_place.sh for exact placement-only generation after the combined w6 gate stops using the shared fork.
- Inherited E7 w4b f7801937e979 spec suffix 1124051025, work suffix 1124051022, remains active. Exact place image pending while generation/preflight progresses. w3c 1124033025 is a physical probe. It does not count even if the old automatic route completes.

## 11-24 07:31 PST exact placement continuation

- W4b `f7801937e979` generated and passed preflight. The inherited route-goal driver selected a detached sealed PLACE waiter on intel2, which never admitted CAD below its 150 GB disk floor. Stopped only that exact pending lane controller and waiter. Preserved their reports as `place_service.pre_review_pin_wait.json` and `place.pre_review_pin_wait.log` in the same private spec directory.
- The exact same W4b kit, `hd_lep0N_w_1124051022`, is now placement-only via `head-west-w4b-place-reviewed.service` and the lane-scoped sealed wrapper. E7 `oth-ubuntu-2381351-1795533662` admitted under the w4b event, permanent kit E7, active sealed materialization `ot-jobs/hd_lep0N_w-place-loved-redfish-2448631-1795533743/work`. The new genuine `place_service.json` supports exact resume after the human view. RTL has both physical-intent station chains, actual placed bank census pending.
- W5 `hd_serdes_1124070219` has the exact corrected dchn FF Liberty SHA 8bc587a4f5b9. Real retry-3 kit_rtl, gen, and E9 gen_lint are PASS; preflight ongoing. W3 diagnostic DRT still running, never count it as W4/W5.
