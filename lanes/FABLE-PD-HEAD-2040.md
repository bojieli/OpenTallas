# FABLE-PD-HEAD-2040 (11-20 21:1x PST): structural review of HEAD plan event R15 (owner lane HEAD-PLAN-R15)

Read-only review, run in parallel with the R15 bind. Nothing cancelled, nothing signalled, no kit touched.
Reviewed: lane dir epyc10 `/srv/opentallas-scratch2/claude/head-plan-r15` (plans p2 435776381eaa = cap-300 re-pick, p2c 2d88d20dccee =
405 no re-pick, p3_cap405 92bcfc338f0a as copied 21:0x = form d), base r13r NOMCAP eccfe487c232 (tools 385f61b5), pinned tools rt
ec4936598992. My outputs: epyc10 `/srv/opentallas-scratch2/claude/fable-pd-head-r15rev/out` (one ot-run unit
oth-ubuntu-435460-1795236274: plan_geom_census x5, event_census x4, event_adopt_diff; plus one reset-tree dump new_trees_405.json).
The 11-19 review of r10 follows below, unchanged.

## Verdict
R15 as composed does NOT fix the reset wavefront class on every writer, and no variant has passed GEN yet (a, c, d all GEN_RTL FAIL).
The 405 scope is the right scope for this event, but the cap is only one of two solver inputs that moved: at 405 the main tools
still build a different reset tree on 11 of 26 types (10 of them signed). R15 should bind the r13r trees, not re-pick names.

## Root causes, with evidence
RC1. START / export / local-reset rows name generated relays by build index (rst_rl_<k>), and the pinned tools renumber and move them.
  - Form c (405, no re-pick), bindrun/r15c gen_rtl.log: hd_ctl now passes, next writer fails:
    `hd_host_n.ad_o: writer START raw reset rst_rl_13 has no registered wavefront driver`. G0 r15c: 4393 errors, all
    `rst_start_raw_N: raw reset export source instance/net/xy differs from actual reset tree`; R-REACH-5 dangling raw names:
    hd_spn_end 205, hd_st_turn 14, hd_host_n 9, hd_tile 4, hd_lep0N 1, hd_st_m 1.
  - Form a2 (300), bindrun/r15gen: `hd_ctl: landing_local_resets.k0: consumer u_cland_fstart_lepk_o0 reset cland_start_raw depth 4 !=
    copy depth 3 (raw rst_rl_132): release edge would move`; G0 5749 errors.
  - Form d (405 + identity re-pick, s1b.py), bindrun/r15dgen: START stages and exports are remapped, local resets are not:
    `hd_lep0N: landing_local_resets.k9: consumer u_cland_sin_agg_coll_i2_1 reset cland_reset_lepk_i0 depth 7 != copy depth 5 (raw rst_rl_482)`.
    Three reference classes exist (reader/writer START stages, reset_start_raw_exports, landing_local_resets); d covers two.
RC2. The main solver is not replay-compatible with the bound trees even at 405. Same plan (p2c), old tools vs rt, cap 405
  (old_trees.json vs out/new_trees_405.json, identity = depth + site + role): 15 types identical, 11 differ:
  hd_tile 239 -> 265 relays, depth 4 -> 5, 171 sites gone / 197 new (gated rst_n_t1 moves depth 4 -> 5: release edge moves);
  hd_lep0N 1431 -> 1405 (56 gone / 30 new); hd_spn_end 452 -> 444; hd_st_turn 268 -> 278; hd_st_m 40 -> 54; hd_host_n 53 -> 57;
  hd_st_str 149 -> 151; hd_mesh_e 14 -> 18; hd_spn_eshim_rx 37 -> 31; hd_spn_eshim_tx 20 -> 18; hd_turn_b 22 -> 22 (12 sites moved).
  The handoff attributes all of it to legal relay sites (42eeacf87f, pushed 19:08 PST, one hour before the pin). That is not shown:
  hd_mesh_e and hd_st_turn only GAIN relays, which a stricter site test alone does not explain; 6 commits touched reset_tree.py since
  385f61b5 (42eeacf87f, e9af887233 R-REACH-1 die/monitor relays, aced0fb210, 4ed355582d, 4ba88d2284, b7b2095a50). Not bisected.
RC3. HEAD carries no bound reset authority: 0 of 26 published wrappers have a .reset_tree.json receipt, 0 of 26 types serialise
  collector_tree, only 4 types had a reset_tree_anchor in r13r. So neither bound_reset_contract (kit gen) nor reset_anchor (bind) can
  hold the tree, and the bound cap exists only as an env value. This is the same class as the 11-20 default-change incident.
RC4. The censuses cannot see any of this. event_census r13r -> R15 reports REGRESS 0 for all four variants (c405, p3_405, c300, p2_300)
  while every variant fails GEN: RESET_ROWS counts plan rows only (hd_tile 9/9, hd_lep0N 26/26), and RESET_UM, UNREG_READS, MON_UM,
  DEFINES_KIT are UNMEASURED without kits (102 of 182 rows). Reset legs and unregistered reads are therefore unmeasured, not clean.

## (1) Scope: 405 vs 300
405 is right for R15: owner 11-20 (defaults come from the bound plan) and "signed types relaunch only when their netlist changes".
Cost of 300 (plan/p3_cap300.log): relays 5,357 -> 7,531 (+41 %), depth deeper on 24 of 26 types (hd_tile 4 -> 7, hd_spn 7 -> 10,
hd_serdes 7 -> 11, hd_lep0N 7 -> 10), all 26 wrappers change so all 25 signed types relaunch, 13 types fail closed in the remap
(no same-depth relay within 405 um, up to 1,246 um), and the die START tree (exports, local resets, START dates) must be re-dated.
But 405 must be recorded as plan/receipt authority (reach_cap_um), and it is not sufficient alone (RC2).

## (2) Census results (R15 compose vs r13r)
- plan_geom_census: R15 rows are byte-identical to r13r in every variant. 11 hops over 300 um on 4 types, none fixed by R15:
  hd_spn be_i 850.5 and bw_i 706.4 (566 bits each), x_o 339.9, b_i 339.8; hd_spn_end be_i 850.5, bw_i 706.4;
  hd_tile line -> u_ad1 573.1 (128 bits), flt_h -> flt_x 420.7, ten_q 398.2, x_q 341.5 (512 bits); hd_lep0N coll_i3 367.6 (514 bits).
  Unregistered reads: UNMEASURED on 6 memory types (hd_mesh 110 macros, hd_host_w 55, hd_lep0N 45, hd_host_e 19, hd_ctl 4, hd_serdes 2).
- event_census: only change seen is hd_serdes DEFINES (+OT_S81_RM_STAGED, OT_S81_KP4_ENC_LA, OT_S81HD_SERDES_RLEAF); REGRESS 0 (see RC4).
- event_adopt_diff: 881 LAG, 17 BOTH, 25 CURRENT; ledger 11 MISSING + 1 DIVERGED in the base, all carried by taking main's tools.
- G0 (lane runs): r13r baseline 0 errors; r15 5749, r15c 4393; r15d not reached. R-REACH warnings unchanged: hd_ctl ring reset fan
  752 um and 8 face buses 2,863 bits up to 362 um from the consumer; hd_serdes ring reset 653 um; hd_lep0N 8 forwarded clocks on a far tap.

## (3) Tap table
Safe for signed types: clock.tap_offset.per_port_ps holds one type only, hd_lep0N (195 -> 251 rows), and hd_lep0N is the unsigned type.
No other type's plan slice changes from it. Two notes: the drift is not a uniform 25 ps but mean -3.9, sd 24.9, range -79.9..+63.6
(port clk +16.6 -> -16.5), and the priced window widens from 150 ps (-100.6..+49.2) to 229 ps (-116.1..+113.3): the table is now
truthful and it shows a die clock delivery spread that hd_lep0N must absorb in hold.
What does relaunch signed types is RC2, not the table: form d changes 10 signed wrappers, and gates15.sh republishes every cohort DIFF type.

## (4) Types most likely to fail on R15
1. hd_lep0N: unsigned; 229 ps tap window; late cores (flop -> core -389 ps, 2,290 ends); GRT overflow 50,446 at round 10 on the epyc10 kit
   (NOPROG 19:30-20:15); blocks GEN in form d (k9); its tree changes, so neither r14 nor tr2s would be the R15 netlist.
2. hd_tile: largest remap (depth 4 -> 5, max move 378 um), 4 hops over 300; its last valid private TT was -52.16 before the ring fixes.
3. hd_serdes: must rebuild (defines); sdr2c lacks the R15 START parent rows, so sdr2c is not the R15 netlist; GRT overflow 1,428 without -allow_congestion.
4. hd_spn_end: 58 START + 14 export remaps, 205 dangling names in form c, two hops of 850 / 706 um.
5. hd_host_n: first writer to fail in form c; 300-um tree needs 644 um moves.
6. hd_st_turn / hd_st_m: trees grow (268 -> 278, 40 -> 54) with 18 / 3 START remaps.

## Ranked fix list (owner HEAD-PLAN-R15 unless named)
F1. Bisect RC2 before anything else: dump the 405 trees of hd_mesh_e, hd_st_turn, hd_tile with rt reset_tree.py at each of the 6 commits
    (1 min each, s1b.py dump). Name the commit(s) per type.
F2. Bind the trees instead of re-picking: R15 = r13r trees on all 25 signed types. Either (a) a plan-recorded site rule + cap for bound
    plans (reset.reach_cap_um 405 and the pre-42eeacf87f site test, scoped like bound_reset_hop_cap; tools change by RESET-RELAY-GEN-R3 /
    FLOW-NOADV-R3), or (b) emit .reset_tree.json receipts for the 26 published wrappers from old_trees.json and let gen.py rtl install them
    as it does in gen_phys. Acceptance: cohort DIFF = {hd_serdes, hd_lep0N} only, G0 0 errors, 0 R-REACH-5 rows.
F3. Put the cap in the plan or receipt, not only in die_gen_env OT_RESET_HOP_CAP_UM.
F4. With F2, make the R15 hd_lep0N rows equal the tr2s source (r14 delta + all251) so a tr2s or r14 sign-off is the R15 netlist; same for
    hd_serdes vs sdr2c (carry the Codex START rows only if sdr2c does not sign).
F5. If F2 cannot land by the apply time: form d may go only with landing_local_resets remapped too, one proof kit of hd_tile through GRT TT
    first, and each DIFF signed type listed with its netlist reason before republish.
F6. Census (PRECHECK / ADOPT-CENSUS owner): add solved reset depth, relay count and site identity per type to event_census, and run it with
    --prev-kits so RESET_UM / UNREG_READS are measured.
F7. Next event: 300-um re-solve with a die START re-date, and the 11 data hops (hd_spn be_i/bw_i first).

## Stop list
S1. Do not apply R15 at cap 300 (25 signed relaunches, START re-date).
S2. Do not let gates15.sh auto-republish DIFF types that are signed.
S3. Do not relaunch any signed type for the tap table.
S4. Do not relaunch hd_tile on the depth-5 tree without a proof kit.
S5. Do not ship 405 as an env-only setting.
S6. Do not read event_census REGRESS 0 as "reset unchanged".
S7. Do not touch r14, tr2s or sdr2c; any of them signing still counts.

---

# FABLE-PD-HEAD-2040: HEAD die physical-design review (r10, hd_tile setup, die intra hold, hd_serdes)

2026-11-19 21:01 PST. Reviewer lane, read-only. Plan reviewed: `head_rp21z20NF15f_r10` (published 20:54 while this review ran; snapshot `s81_head_r10_s0`, private tree epyc10 `/srv/opentallas-scratch2/claude/head-crossing-1119/tree_r10`). Findings against r10 are therefore inputs to the next event (called r11 below).

All host paths are epyc10 unless a host is named. My own runs (private, via ot-run, kit mounted read-only) are in `/srv/opentallas-scratch2/claude/fable-pd-head-2040/tc2/`.

## Summary

1. **hd_tile "TT setup -139.5" is not a TT number and not a window number.** The tilecomb2 flow ran twice. The stage-ODB cleaner deleted the intermediate stage files, so the GRT make rebuilt everything from floorplan in an FF-only session. The DB now routing skipped the TT setup repair, the hold gate and the pre-GRT hold build. -139.5 is its FF setup.
2. **The valid hd_tile number is -52.16 ps after the TT setup repair, and it is the landing-ring status path**, identical for the r8 window (84..123) and the 50 ps window. Behind it sit one 944 um unregistered fault hop (-43.4) and ten cross-tap ends of at most -13.2. With the ring status path registered and the seven centre-spine taps on a 55 ps window, the same DB reads **+14.43 ps, 0 negative ends**.
3. **r10 does not cash the e5c clock for hd_tile.** It keeps the r7 window rows (84..123), and the e5c cluster leaves out two spine taps (clk_t3, clk_t13) that carry the same logic.
4. **The published r9 and r10 snapshots do not contain the kit strap-cut step** that the hd_tile keepout rows assume. Without it the access check passes on 35,095 of 37,203 die clock cells and on 0 of 264 tiles.
5. **Die intra hold: neither -96 nor -248 is a failure of the die clock.** -96 is the all-pair tap skew that the kit windows already cover (kit-contract +1.43, 0 negative). -248 is one type's whole insertion range (hd_host_w, 211 ps at FF) charged to every pair.
6. **hd_serdes:** the two coll_i0 stations are sound. The same unregistered ring status path as hd_tile is present, the ring reset fan spans 554.6 um, and the pma_tck export value (600/500) is not supported by the netlist form.

## A. r10 structural review

### What r10 changes
Plan diff r9 to r10 (`tree_r9` vs `tree_r10` source_plan.json): only three rows change.
- `hd_tile.clock.reserved_sites_um` 4,878 to 6,519 rows
- `hd_spn_wshim_rx.clock.reserved_sites_um` added
- `hd_serdes.clock.pad_clock.pins[pma_tck].export_insertion_ps` added

Plus the die clock directory (e5c `kit_tree.json` 07aa84ac). No pin, window, RTL or lane row changes; bind PASS, cohort 26/26, LATCHECK 329/329, G0 0 errors (`bindrun_r10.log`, `g0_r10.log`).

### Findings

| # | Area | Finding | Evidence |
|---|---|---|---|
| A1 | Keepout / kit tools | The snapshot `gen_phys.py` has no `reserved_pg_cut` (main c113ccf41e5) and no rail keeper (909708562a2). The live r9 hd_tile kit `post_pdn.tcl` sources only pg_island_cut, pg_pin_check and pg_rail_check, while `reserved_sites.tcl` creates 15,722 obstructions including M5-M7 keepouts. HEAD-CROSSING's own access check needs the M6 strap cut: uncut PG gives 35,095/37,203 cells and 0/264 tiles; with the M6 cut 37,203/37,203 and 264/264. | `grep -c reserved_pg_cut` = 0 in `tree_r10/tools/die_plan/gen_phys.py` and in `kw45/snap_s81_head/s81_head_r10_s0`; `kw_r9/items/hd_tile/gen/hd_tile/post_pdn.tcl`; intel2 `~/hc1119/r10_rows.log` |
| A2 | Clock / windows | hd_tile per-port windows are unchanged from r7 (84..123 ps, measured on the e2 tree). The e5c all-pair need is 64..96 ps. The cluster ports keep 90..113, so the kit sees none of the cluster gain. | plan `clock.tap_window.per_port_ps.hd_tile`; `r10/kitwin_fix_e5c_legacy.json` |
| A3 | Clock / cluster | The e5c cluster is clk, t7, t8, t10, t12. The centre channel also holds clk_t3 (342.4, 167.0) and clk_t13 (342.4, 707.0), in line with clk_t10 (342.4, 447.8) and clk_t12 (342.4, 599.0). On the census 48 of 188 negative ends are clk_t3 pairs, and the worst remaining clk-group end captures on clk_t13. | port positions from my `loc.py` run; `fable-fix-head-mesh/su/c2cts/su.log` PAIRS line |
| A4 | Reach | The placed r9 hd_tile kit has 11 register groups over 405 um, 364 bits, 4 groups that need a station, none with a plan row. r10 adds no hd_tile station row and `budgets.r_reach` is unset. | epyc9 `head-crossing-1119/kw_r9/items/hd_tile/geom/placed_scan.tsv`; AUTO-GEOM line in intel2 `~/hc1119/kits_r9/hd_tile/result.json` (r2r 721.98, r2r_count 367, relay_collapse 334) |
| A5 | Clock / lep0N | TAP-OFFSET-GATE FAIL: 329 of 390 hd_lep0N tap checks are outside the offset band, by up to 116.7 ps (clk_c1 -92.8 against band 23.9..43.9). The same line appears on the e2 tree, so r9 has it too. hd_lep0N kits are being built against offsets the die clock does not deliver. | intel2 `~/hc1119/r10_sta_main_e5c.log`; `runs/s81_head/l1119e2r8` and `l1119e5c` sta logs |
| A6 | Windows, margin | On the e5c need, 0 ports are short, but three have 0 ps spare (hd_mesh clk_t15 59/59, hd_st_n4 clk_t22 44/44, hd_turn_b clk_t1 40/40) and six more types have 1 ps. Advisory under R-MINIMAL; noted because the tree is geometry-only and the routed clock will move these. | `r10/kitwin_fix_e5c_legacy.json` against the plan rows |
| A7 | Keepout clip | Confirmed good. No M5 or M7 keepout lies within 0.1 um of the x 6.384 VDD strap column, and no reserved site remains in the window HEAD-MESH-O flagged (x 4.3-6.6, y 646-648): e5c moved those cells. 3,916 of 4,846 keepouts were cut at a strap, none dropped, smallest piece 0.148 um. | my check on the published r10 plan; intel2 `~/hc1119/r10_rows.log` |
| A8 | Pins | No pin row changed r9 to r10. Nothing to flag. | plan diff |

hd_tile groups over reach on the placed r9 kit (limit 405 um, one-cycle estimate 580 um):

| Class | From | To | Bits | Over 405 | Max um |
|---|---|---|---|---|---|
| NEED-STATION | u_b.u_x line | u_b.g_a.g_ais.u_ad1 | 128 | 112 | 598 |
| NEED-STATION | u_b.g_a.g_rir.rir | u_b.g_a.g_ais.u_ad1 | 68 | 24 | 653 |
| NEED-STATION | u_b.flt_h | u_b.flt_x | 5 | 2 | 689 |
| NEED-STATION | g_tenh.u_tenh | g_tenh.u_tenh | 1 | 1 | 722 |
| REACH | u_b.g_sk.u_a line | u_b.g_a.g_ais.u_ad1 | 896 | 208 | 568 |
| REACH | o_row, o_bits | u_bout_o | 49 | 13 | 411 |
| REACH | u_rrl_84 | xv, goo, xvo | 3 | 3 | 461 |
| REACH | u_b.c1 | u_b.c1_h | 162 | 1 | 408 |

### Ranked fix (r11)
1. **Tools overlay: add `gen_phys.py` with `reserved_pg_cut` and the rail keeper** (main c113ccf41e5 + 909708562a2) to the event tree, then regenerate the hd_tile and hd_spn_wshim_rx kits. Until then an hd_tile sign-off on r9 or r10 is a type the e5c die clock cannot land on. Owner: HEAD-CROSSING-1119 (overlay), HEAD-MESH-O (generator support).
2. **hd_tile row, one event** (details in B): `landing_status_reg` + `landing_guard_reg`; station rows for the four NEED-STATION groups and sites for the flt chain; per-port windows re-derived on e5c from data-related pairs.
3. **Die clock: grow the tile cluster to the seven spine taps** clk_t3, clk, t7, t8, t10, t12, t13. They sit on one line at x about 342, y 167..707, so one matched sub-branch along the channel serves them. Report cluster spread over 264 tiles as for e5c. Owner: HEAD-CROSSING-1119.
4. **hd_lep0N tap offsets:** re-derive `clock.tap_offset.per_port_ps.hd_lep0N` from the current tree (`die_sta_related --kit-offset-out`) in the same event, before another lep0N kit signs. Owner: HEAD-CROSSING-1119.

### Stop list
- Stop launching or enqueueing hd_tile route kits from the r9/r10 snapshot tools as sign-off candidates; they lack the strap cut. Running ones stay (owner rule), but do not count them as e5c-compatible.
- Stop carrying window rows across a die clock change without re-deriving the type whose clock changed.

## B. hd_tile setup: root cause

### B1. The -139.5 is an FF number from an accidental second flow pass
- `tilecomb2/gen/hd_tile/run_route.log` holds two complete passes.
  - Pass 1 (TT session, lines 15-2974): `OT_CTS_POST_TIMING setup_ws -406.24` (line 2955), then `OT_TT_SETUP_REPAIR cells 219 added; wns -406.24 -> -52.16 tns -48486.27 -> -192.31`, hold gate PASS (FF -143.04, 10,705 ends), pre-GRT hold build FALLBACK.
  - Pass 2 (lines 2975 on): the `make grt CORNER=BC` call restarts at `2_1_floorplan` with `read_liberty -corner bc` FF libraries only, re-places, re-runs CTS (`setup_ws -139.52`, line 6172) and goes straight to `5_1_grt` (line 6180). No TT setup repair, no hold gate, no pre-GRT hold build.
- Cause: `stage_odb_cap.log` shows STAGE-CAP deleting `2_1..3_5` and `4_1_cts.odb` during pass 1 (01:55, 02:03, 02:40 UTC). Make then found the prerequisites of `4_cts.odb` missing and rebuilt the chain.
- `4_cts_post_hook.rpt` of pass 2 shows clock network delay 445 ps: the tap trees were balanced to the 450 ps target at FF. At TT the same DB has 590 ps insertion (census `su/c2cts/su.log`), 140 ps off the type contract.
- HEAD-MESH-O's census on that DB reads **TT -389.5**, 188 negative ends, all cross-tap. That is the unsized netlist, comparable to pass 1's -406.24 before repair, not to -52.16.
- All six private hd_tile proofs show the same double pass (tilehold, tilecomb, tileproof, tileproof_m4, tilecomb2, tilecomb2n: 2 x `flow.sh 4_1_cts` each). Wave kits show one CTS pass; their route job does re-run floorplan and place once (hd_host_n a9: place ended 13:39, STAGE-CAP deleted at 13:53, route log restarts at 2_1).

Consequence: the tilecomb2 and tilecomb2n routed results will not be valid setup or hold proofs. Their GRT overflow 0 result stands (same keepouts, same strap cut).

### B2. What limits hd_tile after proper sizing
I re-ran the kit's own `tt_setup_repair.tcl` on the pass-1 DB (`4_cts_pre_tt.odb`) and reproduced -406.24 to -52.16 / TNS -192.31 exactly (`tc2/repair.log`). Ends on the repaired DB (`tc2/rpt_rep.log`, placement RC, r8 window):

| Slack ps | Path | Kind |
|---|---|---|
| -52.2 | u_cland_i ring ctl_w -> `u_cland_i/rv` | fclk_in_i to clk, `set_max_delay 416.5` (T/2) |
| -4.2 | same -> `u_cland_i/lap_ok` | same |
| -43.4 | `u_b.flt_h[1]` -> `u_b.flt_x[1]` | zero logic, 6 repeaters, 751 ps of wire; launch (694.1, 63.5), capture (368.2, 681.8) = 944 um; clk_t2 -> clk_t13, window 113 |
| -13.2 .. -3.2 | `pk_h[*]` -> `c1[1][*]`, 10 ends | pick compare, capture window 113 |

Experiments on the same DB (`tc2/rpt_rep.log`, `tc2/rpt2_rep.log`):

| Case | WNS ps | TNS ps |
|---|---|---|
| as built (r8 window) | -52.16 | -192.31 |
| ring status crossing removed | -43.36 | -135.97 |
| + cluster ports clk, t7, t8, t10, t12 at 55 ps | -43.36 | -43.36 |
| + clk_t3 and clk_t13 at 55 ps (seven spine taps) | **+14.43** | 0 |
| every window 0 | +14.43 | 0 |

Reading:
- **Root cause 1, ring status path.** `ot_dp_clk_landing_cas u_cland_i` is built without `STATUS_REG`. The lap/valid compare (7 logic levels) sits on the half-cycle fclk to clk crossing. The RTL already documents this class and its cure (`ot_dp_clk_landing_ca.sv` STATUS-REG-1: "written/lap_q -> lap_ok 480 ps TT vs 416.5 max_delay"). tilecomb2n (50 ps window) has the identical -406.24 and -52.16, so no window setting moves it.
- **Root cause 2, the flt chain.** `flt_q -> flt_h -> flt_x` (bundle RTL line 287) is free-placed. flt_h[1] sits at the elemA1 fault pin in the SE corner and flt_x[1] at the merge under elemB. One hop of 944 um ties clk_t2 to clk_t13 as a related pair. The r9 wave kit shows the same hop at 689 um.
- **Root cause 3, window on the spine.** The remaining ten ends are real cross-tap paths in the centre channel. They close when the spine taps carry a related-pair window of about 55 ps, which the e5c cluster form delivers at FF (35.8) and nearly at TT (44.2).
- **Not a root cause: pick() depth.** The 1,083 ps figure posted at 20:39 is from the unsized pass-2 DB. After sizing the worst pick end is +14.43 with zero window (`pk_h[0][63] -> c1[0][26]`, same tap). The repair targets 0 ps margin, so +14 is where it stopped, not a limit.
- The -406 before repair is the synthesis netlist: x1 drivers at 100-214 ps slew and two fanout-32 BUFx2 selects (census path 1). The kit repair fixes this with about 220 cells; it is expected, not a defect.

### Ranked fix
1. **Make the proof valid.** Relaunch one hd_tile proof with `.keep_stage_odbs` in the kit (or `OT_KEEP_STAGE_ODBS=1`), and confirm one `flow.sh 4_1_cts` in the log before reading any number. Owner: HEAD-MESH-O.
2. **`landing_status_reg: true` and `landing_guard_reg: true` on hd_tile** (type keys, `clock_landings.py` lines 1580-1590). Data and ready keep their cycles, a ring fault is seen one clk later, LATCHECK lanes do not move. Measured effect: -52.16 to -43.36. Owner: HEAD-CROSSING-1119 (plan row), proof by HEAD-MESH-O.
3. **Site the flt chain and add the hd_tile stations.** Put flt_h on the centre channel midway (plan-sited, no cycle), or add one more fault hop; fault is a status flag, not a lane. Add `internal_stations` rows for u_x line -> u_ad1 (128 b), rir -> u_ad1 (68 b), u_tenh, and decide the 896-bit g_sk line -> u_ad1 group (208 bits over 405, none over one cycle) with the same row. Cycles are pre-approved; lane rows refresh as in the r9 hd_serdes event. Owner: HEAD-CROSSING-1119.
4. **hd_tile windows from data-related pairs on the new tree** (`kit_tap_related_pairs.tcl` + `die_sta_related --kit-window-related`, the tool HEAD-MESH-O ran at 13:29), after fix 3 removes the t2 -> t13 pair and the cluster covers seven taps. Measured effect of 55 ps on those seven ports: 0 negative ends. Owner: HEAD-MESH-O derives, HEAD-CROSSING-1119 applies.
5. **`OT_TT_SETUP_MARGIN` 40 for the hd_tile proof kit**, so the repair leaves room for the placement-to-route RC loss (hd_host_e measured -23.70 placement against -77.72 GRT RC before repair, `tt_setup_repair.tcl` header). Existing knob, kit-local. Owner: HEAD-MESH-O.
6. **PICK_SPLIT (+1 cycle) only if a valid routed proof with fixes 2-5 stays below -42.** Today's evidence does not ask for it.

With fixes 2-4 the pre-GRT hold build also keeps its result: it reached +5 ps on both passes and fell back only because the setup base was already under the gate (-52.16 to -57.42, `pregrt_ff_hold.log`).

### Stop list
- Stop quoting `OT_CTS_POST_TIMING` as TT without checking the session corner (`read_liberty -corner bc` = FF).
- Stop reading setup censuses from a `4_cts.odb` that has not been through the TT setup repair.
- Stop treating the window as the cause of hd_tile WNS; it sets TNS and ten small ends.
- Stop waiting on the tilecomb2 / tilecomb2n routed numbers to decide the RTL lever.

## C. Die FF intra hold (-96 contract, -248 with real views)

### Root cause
- **-96.32** (`runs/s81_head/l1119e5c/ca/sta_ca.log` line 63: "hold -96.32 (neg 320308) skew 94.01 kit-contract hold 1.43 (W 13, need 11.57, neg 0)") is the all-pair diagnostic: every tap pair inside a partition, related by data or not, priced with no window. Its size is the 94 ps tap skew inside one partition. The contract that covers it is the per-port kit window, and that check passes at +1.43 with 0 negative pairs. e5c moved it only from -101.07 because the worst pair is outside the tiles.
- **-248.44** (`r10/ca_rv_e5c/hold_report.log`) is not a per-pin measurement. A type view carries only the signed record's `insertion_pinflops` min and max, so every pair of a type launches at the type minimum and captures at the type maximum. 518,784 of 518,810 measured pairs are negative for that reason, same-tap pairs included.
- The bound is set by one type. FF insertion range per signed record (`r10/ca_rv_e5c/real_views/real_views.json`):

| Type | FF min..max ps | Range |
|---|---|---|
| hd_host_w | 298..510 | 211 |
| hd_ctl_n | 256..374 | 118 |
| hd_tile (old-plan record) | 279..369 | 89 |
| hd_st_k5 | 295..373 | 78 |
| all other 16 real types | | 26..71 |

- Six types and all 13 cores are still on contract (hd_host_e, hd_host_n, hd_lep0N, hd_serdes, hd_spn, hd_st_m; signoff.json unreadable or absent).

### Ranked fix
1. **Per-port arrivals in the signed record** (`corners.<c>.port_pinflops {port: [min, max]}`, the DIE-LEVEL-CHECK 20:06 proposal). The die then times a pair with the two ports it really uses, and same-port pairs get full CPPR. This turns -248 into a number comparable with the contract. Owner: DIE-LEVEL-CHECK-1119 for the tool; HEAD-CROSSING-1119 consumes it.
2. **hd_host_w and hd_ctl_n: find what makes a 211 / 118 ps range before their next sign-off.** A range that large on a 450 ps target means either unbalanced tap trees or flops deliberately clocked late (the hd_host_w record is the `outpad5` ECO build). The r8b hd_host_w kit now running should print `OT_TAP_BALANCE done` and `OT_TAP_INSERTION` lines; read those. Owner: HEAD-MESH-O.
3. **Keep hold structural as it is:** cross-tap hold inside a type is built by the kit against its window (pre-GRT hold build), cross-type hold is landed. The die's job is to deliver every window, which it does with 0 to 1 ps spare on nine types (A6). Margin there comes from the routed clock, not from more window.
4. **Re-sign hd_tile and the six contract types on the current plan** so the real-view run stops mixing old-plan records. No action beyond the kits already launched.

### Stop list
- Stop reporting -248 (or QC -355, S81 -438) as measured hold; it is a range bound.
- Stop re-balancing the die tree to move the all-pair -96; it is not a gate quantity and the windows cover it.
- Stop raising per-type windows to chase it (hd_tile already pays 84..123 ps of window in setup).

Owner lane for C: HEAD-CROSSING-1119.

## D. hd_serdes: coll_i0 stations and the pma_tck export clock

No hd_serdes kit has reached CTS on r8b, r9 or r10 (r8 a7 and r8b a2 are placed only). Evidence below is the plan, the r8b a2 kit and its placed-layout scan (epyc9 `kw43-wave-1109n/.../head_rp21z20NF15f_r8b/items/hd_serdes/attempt_2/gen/hd_serdes`).

### Findings
1. **Stations: sound.** st0 (1815, 40) and st1 (1646.5, 79) between the landing band (x 1824.9..2030.1) and the `u_enc.d0` readers (centroid 1478.1, 118.1) give hops of about 150, 207 and 207 um. Taps sit beside both (clk_t18 at 37 um from st0, clk_t14 at 32 um from st1). +2 cycles on the 12 coll_*_d lanes are priced; LATCHECK 329/329.
2. **Ring status path, same class as hd_tile.** `u_cland_coll_i0` is `ot_dp_clk_landing_cas #(.W(515), .DEPTH(4), .WREG(1), .DSREP(8), .WRITE_CHUNK(16), .RSTREP(19), .PLACEREP(1))` with no `STATUS_REG`; the kit SDC has `set_max_delay 416.5 -from fclk_in_coll_i0 -to clk` (`rtl/ot_s81hd_serdes.sv` line 73, `constraint.sdc` line 51). Expect the hd_tile result (-52 on rv) at its first CTS.
3. **Ring reset fan over reach.** `u_cland_rst_coll_i0/q` drives 28 loads across 554.6 um (bbox x 1470.7..1977.8); the stations moved data, not this reset (`run/layout_review/place/smells.json`, fanout_spread, 579 nets flagged).
4. **Tap table no longer matches the sinks.** G0 on r10: 10 of 22 explicit taps empty (clk_t3..t8, t10, t12..t14), clk_t20 load 5,940 against cap 1,000 at radius 329 um, clk_t21 radius 487.6 um (`g0_r10.log`, TAP-LIMIT-INFO). The kit will re-assign by distance, but the taps were materialized on 11-13 before the stations existed.
5. **pma_tck is a wire from the clk port, not a leaf of the type tree.** `ot_pdie_serdes.sv` line 64: `assign pma_tck = clk;`. The kit hook (`phy_clock_export.tcl`) accepts only a BUF/INV chain back to an input port. The SDC makes pma_tck a generated clock of port clk, and `pma_tx[*]` is constrained against `vclk` (latency 450 TT / 380 FF), not against pma_tck.
   - If the branch is before the tap pad chain, the pad clock leaves about 150 ps after the port and pma_tx about 450 ps + clk-to-q after it: the clock leads the data by roughly 300 ps plus clk-to-q.
   - The r10 value `export_insertion_ps {TT 600, FF 500}` assumes the branch is after the 450 ps tree. That is 450 ps different, more than half a cycle, and it changes which pma_tck edge captures pma_tx.
   - Not measured: no hd_serdes CTS DB exists on this plan. The leg is 399 um Manhattan from the clk port (1439.3, 20.4) to the pin (1114.7, 148.3); the nearest tap (clk_t2) is 267 um away.

### Ranked fix
1. **`landing_status_reg` + `landing_guard_reg` on hd_serdes** in the same event as hd_tile. No lane cycle changes. Owner: HEAD-CROSSING-1119.
2. **Fix the pma_tck form in the plan, then measure.** State in the pad_clock row where the clock branches (at the port, before the tap pad chain) and constrain `pma_tx` output delay against the `pma_tck` generated clock, so kit STA times the real pad relation. Set `export_insertion_ps` from the first hd_serdes `4_cts.odb` (arrival at port `pma_tck[0]`, and the `OT_PHY_CLOCK_EXPORT` log line), and mark it measured. Until then label 600/500 as unverified in anything that consumes it. Owner: HEAD-CROSSING-1119.
3. **One sited repeater on the pma_tck leg** (399-453 um, over the 405 um hop) at mid-leg, so its insertion is the same in every build. Owner: HEAD-CROSSING-1119.
4. **Reader-start/reset trunk for coll_i0** (`reach_rules.py fix --rules 1`, `landing_reader_start` with `share_trunk`): one relay at st1 for the loads near x 1470. Boot cycles only. Owner: HEAD-CROSSING-1119.
5. **Re-materialize the hd_serdes explicit taps** from the r8b a2 placed DB (the HEAD-98 method), so the band around clk_t19..t21 has taps for about 7,800 sinks at cap 1,000 and the empty taps go. Owner: HEAD-MESH-O (type kit), row applied by HEAD-CROSSING-1119.

### Stop list
- Stop using 600/500 as the pma_tck insertion in any die-level number until a kit measures it.
- Stop adding stations for data buses without the matching reset/start relay for the same span.

## Flow note for the flow owner (outside both lanes)
STAGE-CAP (11-17) deletes `2_x` and `3_x` stage ODBs after the place job. The wave route job then re-runs floorplan and place before CTS (hd_host_n attempt_9: `run_route.log` starts at `2_1_floorplan`). It costs one full placement per kit and the routed DB is not the placed DB that AUTO-GEOM read. In the private hd_tile proofs (copies of an r3 kit, whose GRT make runs FF-only) it also caused the double pass of B1. Reported here as a measured fact only.

## What I ran
- `ot-run --hosts epyc10`: the kit's `tt_setup_repair.tcl` on a copy of `tilecomb2/gen/hd_tile/4_cts_pre_tt.odb`, then end reports and window experiments in the same frame (`tc2/repair.log`, `rpt_pre.log`, `rpt_rep.log`, `rpt2_rep.log`), and an ODB location dump (`loc.py`). Kit mounted read-only. No kit, plan, job or main change.
- Not checked: routed numbers for any fix above (all figures are placement RC on a CTS-stage DB); the pma_tck branch point in a built hd_serdes; the cause of the hd_host_w insertion range.
