# FABLE-FIX-QC-COLL handoff (Fable; owns QC coll_core end to end since 11-21 19:25 PST; successor of FAM-QC-COLL-R3 for coll_core)
Work dir: epyc7 /srv/opentallas-scratch2/claude/fable-fix-qc-coll (an/ = analysis + solver, pkg/ = composed plans, pk1/ = private bind, reset/, faultgen/).

## Method (close by construction, measured on the pkit10_wall placement)
- an/grp.py: group-level register-to-register reach through ALL logic (not only zero-logic links): 9,089 captures over 405 um in 312 group pairs.
- an/solve.py + cfg3.json: every reg-to-reg connection is a constraint L1 <= 370 um (330 to a macro box); soft flops move by constraint projection;
  result 14,516 violated edges -> 926 (20 pairs, list in an/s3/residual.json). Seats for ALL 49,530 GPL-placed flops = plan relay_sites (FIRM, 0 cycles);
  hook-placed flops (ring, face, reset relays, stations) are untouched.
- Stations by measured length (+cycles): rec_tx_s0 1->3, rec_tx_s1 0->2, rec_tx_s2 0->2, flt_o 0->3, fltv_o 0->3 (per-bit seats, sites=float),
  io_collective__fault 0->3 as three parallel OR groups (kit_istations or_groups, main 2c3fa5fd9727).
- Reset: the u_rrl_221 groups are a 3_place read artefact (reset_taps.tcl re-points leaves post-place, max 91 um); only 4 seats for the two face reset syncs.
- Residual after seats (needs RTL stage or a core move, not in this package): hi_q/lo_q -> g_pf fold slices 254 bits at 411 um (box distance),
  tbc/pe_q <-> g_pf_3 6 bits at 558 um, PIN shr_p_rx_i -> landing ring sd_c 467 bits at 441 um (ring structure).
- relay-mid: QC chain regex is on main 00377e9dc84a (default for qwen_compute); on coll_core every chain flop is seated, so the hook has nothing left to place.

## Package
- compose: an/compose.py PLAN_IN PLAN_OUT an/s3/seats.json reset/rows_reset.json faultgen/run1/row.json ROWS.json (idempotent wall respace included).
- pkg/plan_v3p3_coll.json = V3p3 f5d51696a2eb + package; pkg/lat_v3.json = same after gen.py latency (13 lanes change, 1921 lanes).
- pkg/plan_v2.json / lat_v2.json = V2+wall base for the private proof. Needs tools >= 2c3fa5fd9727 (schema key or_groups).
- Every coll_core kit: OT_KEEP_WIRES += ot_reset_sync:reset_pipe qfd_static_ch546:r_reset_meta.

## Live units / waiters
- see the posts in lanes/posts/FABLE-FIX-QC-COLL.md (latest line wins).

## STAND-DOWN 11-21 ~22:0x PST -> FABLE-FIX-QC-COLL-R2 (context). Nothing cancelled. Re-arm a waiter on each unit first.
LIVE UNITS
1. Private strict bind + LATCHECK + kit-rtl of the package (V2 base, tools 2c3fa5fd9727): epyc7 unit oth-ubuntu-3314323-1795319375,
   script epyc7 fable-fix-qc-coll/bind_pkg.sh, client log fable-fix-qc-coll/bind_pkg.client.log, outputs fable-fix-qc-coll/pk1/{bind.log,latcheck.json,rebind,rebind_rtl,kit_rtl.log}.
   Ends with COLL_PKG_BIND_DONE. Plan bound = pk1/bind_plan/zz_coll_core_pkg.json (= pkg/lat_v2.json). Tree epyc7 kw45/snap_qwen_compute/qwen_compute_v2r10_famqc
   (made by the script from pk5/pk6), launch tree rt_tools_launch/qwen_compute_v2r10_famqc@2c3fa5fd9727. NOT yet read: this is the first bind of the or_groups row,
   the sites=float fltv_o row with relay_sites station keys (u_ist_fltv_o_<j>/q[b]) and 49,748 relay_sites keys; expect possible schema / native-receipt findings.
2. reflow3 (COLL-R3: reflow2 + 10 face_0 u_ctl seats at (300,75)): intel2 unit oth-ubuntu-2919937-1795318838 (client otrun-tolerant-swine-2918428),
   dir intel2 fam-qc-coll/reflow3. place.client.log ends with an earlier attempt (unit 2881460, do-3_3_place_gp Error 1): check place.client.r1.log / which log the live unit writes.
   Its question (es -> fault_cause 500 um) is already covered by the seat solver (all face codec u_ctl flops are seated); use reflow3 only as a cross-check.
3. coll_ftc V2 wave kit a1 (not ours to cancel): epyc8 .../kit-wave/qwen_compute/s29q103S4Q9N46R6V2/items/coll_ftc/gen/coll_ftc; wait with ot-wait --kit <that> --host epyc8 --stage grt, then route / finish.
   reflow2 (intel2 unit oth-ubuntu-345723-1795315461) ENDED rc 0, placed; ideal-clock WNS -367.5 (COLL-R3 read).

STATION PLAN FOR THE 92 GROUPS (all in pkg/, rows report pkg/rows_v3p3.json)
- Record TX (705 bits): rec_tx_s0 3 stations (440,1000) (266,1112) (275,1351); rec_tx_s1 2 at (460,480) (480,130); rec_tx_s2 2 at (475,560) (478,180).
- Fault vector / fault outputs (~25 groups): fltv_o 3 per-bit stations; flt_o 3 at (15,650) (15,960) (15,1270); io_collective__fault 3 x 3 OR-group stations (Codex reflow sites).
- u_coll internals, record RX landing chains, face memory legs (737 + 760 + 174 bits): 0 cycles, seats from the solver (relay_sites).
- Reset u_rrl_221 groups (~45): no row (post-place leaf re-point); 4 reset-sync seats.
- Forwarded clocks clk_t41/t42 -> fclk_out_* (11 groups): clock nets, R2 fix14 rule-4 rows (already with QC-PLAN-R12); not re-done here.

NEXT STEPS (R2)
1. Read the bind: strict 0 + LATCHECK 1921 with exactly the 13 lanes of the 21:xx post changed. Fix findings in an/compose.py (never by hand in the plan), recompose both bases.
2. Write lanes/handoff/FABLE-FIX-QC-COLL-V3-pkg.json for QC-PLAN-R12 before 04:00 (cut 06:00): plan path pkg/plan_v3p3_coll.json + lat_v3.json, compose command, rows report,
   bind / LATCHECK receipt, tools >= 2c3fa5fd9727, RTL = main aaa1dcff0349 ot_coll_tp8_static.sv (pk5) + six defines, keep-wires env, residual list. Ask R12 whether +2 on the
   record lanes and +3 on fltc / fltvc may ride V3 (posted as HEADS-UP 2; no answer read yet).
3. Private proof: on intel2, python3 -I /srv/opentallas-scratch2/claude/rt/2c3fa5fd9727/tools/autopilot/kit_wave.py private-spec qwen_compute coll_core
   --plan <epyc7 pk1/bind_plan/zz_coll_core_pkg.json> --tree <epyc7 snap>/qwen_compute_v2r10_famqc --src-sha aaa1dcff0349 --bind-out <epyc7 pk1/rebind> --rt 2c3fa5fd9727
   --host epyc7 --work fable-fix-qc-coll/pkit1 --out intel2 fable-fix-qc-coll/pspec1 --lane FABLE-FIX-QC-COLL-R2
   --ab "OT_KEEP_WIRES=<wave value + ot_reset_sync:reset_pipe qfd_static_ch546:r_reset_meta>" --why "merged reset flop 719 loads (pkit8 proof)"; the full wave value is in
   epyc8 fam-qc-coll/pkit10_wall/wave_spec.json gen_env. Diff config.mk against the wave coll_core kit, then kit_wave.py run-item <spec> ON intel2 (pspec10wall is the template).
4. In the place log check: OT_RELAY_SITES unmatched count (was 5), OT_ISTATIONS, 9 fault stations + 207 fltv seats placed; then rerun an/grp.py on the new geom.tsv
   (target: captures over 405 from 9,089 to the residual list), geom read WITH the kit pin contract, post-hook CTS, final 5_1_grt.odb, route, sign-off, export.
5. Residual: hi_q / lo_q -> g_pf slices and tbc / pe_q <-> g_pf_3 (move g_pf_3 next to g_pf_0..2 or one RTL stage); decide on the placed read of the proof kit.
UNVERIFIED: no kit has run with these seats; ff_put_near with 49.7k keys and seat density (512-bit banks projected to one point) are untested; solver uses macro box distance, not pin faces.
