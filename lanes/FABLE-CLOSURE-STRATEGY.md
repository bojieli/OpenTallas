# FABLE-CLOSURE-STRATEGY 2026-11-16 21:40 PST (2140): the per-port tap window is the common hold cause; S81 col now fails at route, not only at relay depth

Reviewer: FABLE-CLOSURE-STRATEGY-2140 (Fable). Read-only. Technical PD only. HBM parked.
Gates: DRC 0, routed TT >= -42, internal reg-to-reg FF hold >= 0, die bind + LATCHECK, die clock gate (routed pair setup >= 0, hold >= +10).

Read 21:05-21:20 PST: strategy 2100, FABLE-PD-S81-STRIP, -QC-MCLK, -HEAD-2045, FABLE-PLAN-S81-B6gF2s5f, -KV-HG3, FABLE-FLOW-2000
(technical lines only), handoffs S81-TYPES-R2, S81-SERDES-R2, KV-CLK-R2, KV-HUB-WO, KV-R-CODEX-PARK, QC-CLK-R2, QC-PLAN-R, QC-TYPES-R,
HEAD-TYPES-R2, HEAD-DIE-R, queue posts 19:00-21:11, `failure_breakdown.py` 21:10.
The five FABLE-FIX handoff files (S81-BKSEL, S81-STRIP, QC-DIECLK, HEAD-SERDES, S81-IFN0-HW) do not exist yet; I read those lanes' queue posts.
There is no S81-DIE-R2.md or KV-R.md handoff either (S81-DIE-R.md and KV-R-CODEX-PARK.md only).

MEASURED by me (log tails, 21:11-21:15): col pilot route logs on intel2 `~/fable-fix-s81-coltap/pilot5*_route.log`; bksel `hei_eco.out` / eco2
`run_prd.log` (epyc2); HEAD `hei3.log`; H3p GPL log (epyc8); KV `hg2cgate/gate.out` (epyc10); S81 `log/B6gF2s5f.log` (epyc10); strip ov25 pilot logs.
Everything else is REPORTED by the named lane. INFERENCE is marked.

## 0. Verdict

1. **One mechanism now explains the large hold-cell debts on three dies: the per-port tap window in the kit SDC.**
   QC cbn_q01 proved it (21,467 endpoints at -211.66 with windows 63-248 ps; 1,736 at -81.55 with 10.1 ps rows; 0 after one
   repair pass, 2,369 cells instead of 36,093). KV rows C carry per-port windows up to 202 ps (mean 72.4), and HEAD shows
   12,346 cross-tap ends at -112 (hd_mesh), 5,212 at -88 (hd_ctl), 24,119 HB4 on hw5. KV and HEAD have not been read for it.
2. **S81 col (203 types) has a new limiter at route.** The three old-form pilots ended between 21:04 and 21:11:
   col_h9_r1 failed GRT (max 119 %, 28,663 gcells over 90 %, local density 0.985), col_h9_r2 failed detail route with DRT-0255,
   col_h10_r2 routed DRC 0 but its sign-off STA did not run. The D4 col-wave1 pilot is the same col_h9_r2 type.
3. **S81 strip leaves (75 types): cause is measured, fix is a setting plus form B.** GPL drifts at die scale between overflow
   0.25 and 0.10. The fix must be in the tree before the kit_rtl repair releases 29 leaf items in the old form.
4. **QC die chain is clean on clock rows; two things are open:** the count frame (23 lanes below zero latency) and cb setup,
   which no proof has read (-294.44 estimate on the old source).
5. **HEAD is at 5 stand-ins.** host_w is 4 endpoints from sign-off and stopped on a file-permission error.

## 1. The 21:00 levers: done, open, wrong

| # | 21:00 lever | state | evidence |
|---|---|---|---|
| 1 | one RC table for repair and sign-off | **OPEN; bksel premise WRONG** | No both-table WNS print landed. HEAD measured the slip instead: GRT to route 6-17 ps (hw4 TT 16.8, FF 12.8). bksel fx6's 51 FF endpoints are not an RC-table residue: 46 are hist-bank macro input pins (g_bank[3] i_dg / i_en, worst -5.8), 2 are t_o_f D at -16.09 from 64 ps leaf skew. The auto planner skips macro pins |
| 2 | S81 col relay depth as plan rows; NOFIT fails at gen | **PARTLY** | D4 tree carries the relay regex, pair_skew fix and fail-closed gen. 8 of 18 NOFIT groups of h10_r0_p1 are row-fixable (one xo_o0 row, 3 stations, max hop 390, +3 cycles, 7 types) and go into C4. 10 groups need relay depth in the col RTL generator: not started. bs1 mirror fix: posted as a row, unproven (rm4 is evidence only, 16 unfitted) |
| 3 | SerDes cross-tap: H3 plain launchers, G3 re-pitch, bind rule | **bind rule DONE in s5f; G3 cause WRONG; H3p no number** | s5f drops all 11 serdes types from relay_lockup. H2 at GRT: 3 violations, all u_rrl_33 -> u_rrl_38 (-57.76), internal FF +0.17. H3p is still in global placement (first try died on the boot-release selector). G3: clk_t14 holds 5,925 u_enc flops, not rm.mem; the fix is encoder-stage cohorts, not a uniform 117 um pitch. J5 parked at -1,138.95 |
| 4 | CTS-stage hold on every two-mode build | **DONE on proofs; W0/W1 OPEN** | headseg44 hf signed (TT +133.23, DRC 0, internal FF 0). coll_n generic stage: 63 endpoints, 86 HB4, 149 nets, DRT 0, TT -1.39, internal FF 0. W0 in DRT, W1 at floorplan |
| 5 | HEAD 7 stand-ins by defect | **7 -> 5** | host_e he12h_drc2 and hd_spn (NF13a view equals NF15c: 6,371 pins, 0 moved) are real parts. hd_tile TP2 signed (TT +12.07, 34 HB4). Open: host_w, serdes, mesh, ctl, lep0N |
| 6 | QC rows from exact readout | **rows DONE; not adopted** | s4q9m_r CHAIN_DONE: CA 2,993 FAIL 0, SPEF half range p90 0.3, cb tol <= 10.2, TAP-OFFSET-GATE 0 / 84,512, FF kit-contract hold +10.00. New blocker: count frame on l2d |
| 7 | KV: bind HG2, pilots, child cores, hub_Wo band | **bind running; 7.4 WRONG** | HG2c PRE PASS, G0 PASS 0 errors, bind running. The hub_Wo cause is an ft-station comb (1.080 um gaps, cell 1.188), not the band. The 5 child cores are existing views registered as candidates, yet the wave still listed 6 parents waiting at 20:41 |
| 8 | bksel structural landing if fx6 misses | **OPEN, changed** | fx6 routed FF -16.09 on 51 endpoints; 212 internal pins under +10. Hold-only ECO (213 HB4, macro pins included): first run route_rc 2 at 20:57, second run (eco2) in DRT pin access at 21:12. Wire landing is not the limiter |

## 2. Levers now, ranked by types / dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col: route-stage diagnosis on the three pilots before col-wave1; relay depth in the generator | 203 col types | S81-TYPES-R2, S81-DIE-R2; one Fable PD review |
| 2 | QC, KV, HEAD | per-port tap windows from exact tree readout; cross-tap hold read at post-CTS on the first kit of every clock event | QC 18 cb types / 192 partitions; KV all 51 clocked types (INFERENCE); HEAD mesh / ctl / host_w | FABLE-FIX-QC-DIECLK, KV-CLK-R2, HEAD-DIE-R |
| 3 | S81 | strip leaves: GPL exit at overflow 0.25, form B at the bank end, dswp copies, in the tree before leaf kits launch | 75 leaf types | FABLE-FIX-S81-STRIP, S81-DIE-R2 |
| 4 | QC | S4q9m: count-frame re-frame, then cb pilot that reads setup as well as hold | QC die clock gate; about 100 QC types on clock rows | QC-CLK-R2, QC-PLAN-R, FABLE-FIX-QC-DIECLK |
| 5 | HEAD | finish host_w (4 endpoints), sd9c GRT read then sd9d, NF15d, HEI on mesh / ctl / lep0N | HEAD die clock gate (5 stand-ins) | HEAD-HW-ECO, FABLE-FIX-HEAD-SERDES, HEAD-DIE-R, HEAD-TYPES-R2 |
| 6 | KV | HG2c bind -> HG3 with the hgi_v8 move folded; hgi and hg gen classes | 11 hgi + 6 hg types, hub_Wo, 31 pilot-held keys | KV-R, KV-HUB-WO |
| 7 | S81 | SerDes: H3p to a CTS number; encoder cohorts for G; J floorplan | 11 serdes types | S81-SERDES-R2, S81-DIE-R2 |
| 8 | S81 | bksel hold-only ECO; IFN0 HW trunk reseat routed proof | dsdv_bksel_q + 7 bk_sel types; rom_q halves | FABLE-FIX-S81-BKSEL, FABLE-FIX-S81-IFN0-HW |

### Lever 1. S81 col: the route stage (203 types)

Evidence (MEASURED, route logs on intel2, old-regex `gen/` kits on the D3 tree):
- col_h9_r1 (cl49d7a23e pv047ea3b3): GRT exit 2 at 21:09. Render flags: GRT max 119 %, 28,663 gcells over 90 %, local density 0.985,
  channel_tracks 9.7, fanout_spread 1,218.
- col_h9_r2 (clce45cab5 pv7a260fc0): detail route stopped with DRT-0255 after 45 min. GRT max 100 %, 279 gcells over 90 %.
- col_h10_r2 (cl1f5d6c2a pv0c1de895): routed, DRC 0, antenna 0, pin audit 1,617 / 1,617. Sign-off printed setup_tt NOT RUN, hold_ff NOT RUN.
- rm3 col_h10_r2 (per-bit istations, CTS -39.0, 0 under -42) resumed route at 20:16; no result yet.
- REPORTED: rm2 col_h10_r2 at GRT -172.0 on 2 endpoints (so[1:0] -> ist_frame_int_o0, 1,131-1,320 um) = site class, fixed by rm3 sites.
- REPORTED: 13 station rows over 405 um in the adopted plan, 12 of them col_h10_r1 `bus:frame_int_i0` at 422.6 um.

Root cause. Not diagnosed. The three failures are three different stages on three types, so col has no routed timing number at all.
h9_r1's density 0.985 with 28,663 hot gcells points at placement (FIRM station / relay rows filling bins), not at a route setting (INFERENCE).

Fix.
1. S81-TYPES-R2, now: run the sign-off STA on the col_h10_r2 routed DB (same frame as the kit). It is the first col routed TT / FF number.
2. S81-TYPES-R2: open the h9_r1 GRT congestion report and the h9_r2 DRT-0255 net and route box; post net name, layer, coordinates and
   what sits there (station row, relay row, macro pin, clock band). No relaunch before that.
3. COORD: one Fable PD review on those two (FABLE-PD-S81-COLROUTE). Inputs: the two kit dirs on epyc8 and the place / GRT renders.
4. The D4 pilot (col_h9_r2 clce45cab5) is the type that just hit DRT-0255. If the D4 kit differs from the `gen/` kit only by the relay regex,
   expect the same stop; read its GRT hot-gcell count before spending the DRT.
5. S81-TYPES-R2: relay depth in the col RTL generator for the 10 non-row groups (lpl_11_r 1 -> 3 stages, lpl_12_r, rr_1, so_1, so_3, x2_3
   1 -> 2, es_p0 2 -> 4, xa_1 / xb_1 3-stage tree), legal sites from `groups_h10_r0_p1.json`. Cycles back to S81-DIE-R2 for the lane latency.
6. S81-DIE-R2 in C4: the xo_o0 row (7 types), the bs site row, and the 12 col_h10_r1 frame_int_i0 rows at 422.6 um.

### Lever 2. Tap windows from exact readout, on every die

Evidence.
- QC cbn_q01 (MEASURED by FABLE-PD-QC-MCLK and FABLE-FIX-QC-DIECLK): all 21,465 register paths are rise -> rise across tap ports; the window
  term is 66.7-243.7 ps per pair; the trees themselves match to 2 ps. With S4q9m cb rows (tol 10.1): 1,736 endpoints, worst -81.55;
  one pre-GRT pass leaves 0 at +5.00 with 2,369 cells. Decomposition of the 707 flop pairs: 634 fail only by the 22 ps window,
  65 fail on an ideal clock (zero-logic pipes against 25 ps uncertainty).
- KV (REPORTED, KV-CLK-R2): rows C = need + 10 from the GRT readout, 6,129 per-port windows, max 202, mean 72.4. kv3_pv_v8 ended at the
  12 h cap in post-route hold repair at iteration 620, hold unmeasured: the same signature as cbn_q01's 450 iterations (INFERENCE).
- HEAD (REPORTED, FABLE-PD-HEAD-2045): tap means 396-460 on sd9c (spread 65), clk_t6 356 against a 450 target on hw5; hd_mesh 12,346
  cross-tap ends at -112; hw5 15 % of logic cells are HB4. A hold cell on the capture pin cost sd9A 57.2 ps of setup on rem_q.

Root cause. Windows cut from GRT readout spread (gcell phase adds 0-21 % wire per instance) are 5-20 times the real same-type spread.
The kit SDC turns each window into cross-tap hold debt, and the debt is paid in hold cells that then tax setup.

Fix.
1. KV-CLK-R2: take the e6a per-port spread from an exact-length clock SPEF (the `clock_spef.py` / rows_m.py path QC used), compare with the
   202 / 72.4 GRT windows, and post the table. If the exact half range is under 20 ps on templated types, re-cut rows C as tol = exact + 10
   and carry it on HG3 or the next KV event. Windows do not move taps, so rows B stay.
2. KV-R: first pilot (kv3_pv_v1n) stops at the post-CTS FF hold gate and prints cross-tap endpoints and worst slack before GRT.
3. HEAD-DIE-R: same read for NF15c tap rows on hd_mesh and hd_ctl (they are at GRT / route now; read their post-CTS DBs, no rebuild).
4. FABLE-FIX-QC-DIECLK: merge dd226b837fa (lockup latch `u_lk_nk_*` on its launch tap; accept on endpoint / TNS gain; guard reads per-port
   lines). KV and HEAD kits use the same `clock_taps.tcl` and `pregrt_ff_hold.py`, so the two rules apply there unchanged.
5. All: no hold cell on a capture pin whose setup slack is below the cell delay (HEAD class fix 3); pad the short branch.

### Lever 3. S81 strip leaves (75 types)

Evidence (FABLE-PD-S81-STRIP, FABLE-FIX-S81-STRIP; MEASURED by them). GPL exit HPWL / run minimum: t47 2.36, t75 1.91, t8fix 1.81; t28 / t34 /
t62 / t72 1.01-1.05. On t75 between overflow 0.25 and 0.10 the median movable cell moves 98 um, 61,962 of 125,066 move over 100 um.
Exit at 0.25: 1.026 x, DPL max displacement 91.6 um, 0 failures. Exit at 0.20 sits on the knee (t47 1.26). Density 0.65 / 0.9, TD off and
keep-resize 0 do not stop it. The vpw arbiter adds 285 failing endpoints on every leaf (VS clk -> x_wa 383 ps, then 5 levels and up to 751 um).
No leaf is near -42 at kit RC (t62 -216 best, t34 -478). The ov25 proofs with TD on were at GPL iteration 0-30 at 21:11: no CTS read yet.

Root cause. (a) At under 1 % movable utilisation the last Nesterov phase pushes ring and vpw logic away from FIRM flops. (b) The five-writer
vpw arbiter sees raw VS outputs in one cycle. (c) `driver_dswp_q` is one flop for registers 300-500 um away (t62: 601 paths, -548 at x1.45).

Fix.
1. FABLE-FIX-S81-STRIP: sparse kits exit GPL at overflow 0.25 as the S81 flow default (branch claude/s81-strip-gpl-stable-1116), PLACE-HPWL 1.3
   kept as the net. Adopt on the CTS read of t47 / t75 against -2,642 / -1,047 at kit RC.
2. S81-DIE-R2: form B (XR stage at the bank end, +1 on the write bus) and per-slice dswp copies in the C4 bind. XR flops in a region at
   u_b0 / u_b1 on a standard tap. Pilot t34 (501 um) and t62 to a reloaded-GRT read before volume.
3. Ordering: the kit_rtl repair (r437, D5 tree) releases 29 leaf items. D5 must carry fix 1, and leaf kits on a bind without form B stop
   at the post-CTS read. Otherwise 75 kits repeat the 285-endpoint failure.
4. t43 stays out until the catch-all station row for u_vs.s_d (156 b), s_v and fault is delivered (B6gF2s5f watch 1).
5. Check the same drift on SerDes: H3p's GPL log shows `ring_place=ff` leaving 10,134 ring logic cells per landing to GPL and HPWL rising
   +7.8 % at overflow 0.85 (MEASURED, epyc8). Read exit HPWL / minimum on H3p before its CTS census.

### Lever 4. QC: re-frame, then a cb pilot that also reads setup

Evidence. `--cap-in` rehearsal on l2d: 2,525 crossings FAIL 0, but 23 lanes have clock_landing below zero (c_E*_bn_11__b12 / tn_11__b12,
-1 / -2). The count frame is still the forward-feed wall-aligned frame while the comb clock lands regions whole cycles earlier.
cb setup: the what-if kept TT setup estimate -294.44 at post-CTS (old S4Q6D source, placement RC). cbx_q10 read -1,803 / -1,928 without the
r301 xcst fanout fix. slw_st_b_v1 failed the post-CTS setup triage at 21:09 on the current event.

Fix.
1. QC-CLK-R2: plan `clock.spine.feed` = comb feed with frame_offset = round(built leaf TT arrival / T) per region, CA re-run with
   `--frame-plan`, then `sta --cap-in`. Pass = 0 lanes below zero and LATCHECK equal on unchanged lanes.
2. FABLE-FIX-QC-DIECLK: the cb pilot (cbn_q01__clab6e67f2, S4q9m cb rows, r301 source) also prints post-CTS TT setup by class.
   Gate for the wave: cross_tap <= 2,000, ws >= -90, 0 latch endpoints, and TT setup estimate >= -100 with the worst class named.
3. QC-CLK-R2: DRT + RCX of one cb region against the SPEF offsets (offsets are calibrated to the GRT mean; LE 12 -> 16 moved them 22.6 ps).
4. QC-TYPES-R: read the slw_st_b_v1 worst path (job d109c3f8af24) before any relaunch.

### Lever 5. HEAD: 5 stand-ins

Evidence. hw4e2 sign-off: DRC 0, TT -29.73, internal FF -10.77 on 4 endpoints. hei3 inserted 4 HB4 at 4 pins, then exit 1 on
`cp ... hei3/libraries.json: Permission denied` (MEASURED, 21:08): no route ran. sd9c GRT: 0 overflow, then a flow error (measured-hold
census saw 2 clocks); fixed in the kit and resumed from 4_cts.odb at 21:05. mesh post-CTS TT -5.80, ctl +1.60, lep0N in CTS at 310,983 cells.
The wave's own hd_host_w (job c03e0b859913) ended TT -43.57 after one late ECO: 1.6 ps short, superseded by hw4e2 / hw5.

Fix.
1. HEAD-HW-ECO: rerun hei3 in a directory the job user owns (the insert plan is 4 cells), route touched nets, sign-off. Fastest view of the five.
2. FABLE-FIX-HEAD-SERDES: at sd9c GRT read rem_q slack, launch / capture arrival and any HB4 on its D pin. At <= -25 skip DRT and build
   sd9d (all u_enc.rem_q on one tap, no capture-pin hold cell under 60 ps setup slack).
3. HEAD-DIE-R: NF15d (u_chn 1548.0, 109.44) through G0, bind, LATCHECK; real-view die STA real3 (21 real parts) for the first seam read,
   host_w coll_o0 port hold first.
4. HEAD-TYPES-R2: one HEI pass each on mesh, ctl, lep0N at first sign-off; lep0N cell count after hold cells against the 400k cap.

### Lever 6. KV

Evidence. HG2c: PRE PASS, G0 PASS (0 errors, 56 types / 160 partitions), bind running (MEASURED 21:12). HG3 = HG2c + 13 leaves; hub_Wo windows
at x 545.6 / 550.5 give 45 slots in 15 of 15 rows. Model sweep of 5,170 raw-stage windows: kv3_hgi_v8 fs_ft11_o stages 1 and 2 have 0 slots.
Gen classes: 11 hgi types `core_cloc` plan metadata, 6 hg types frozen-tool mismatch (views w652 / w653 / w672 packaged with tool 5083985a
instead of 7ecd3a0d).

Fix.
1. KV-R: fold the two hgi_v8 moves ((1215.0, 771.048), (1215.0, 391.074), hops 379.2 / 380.0) into HG3 if its bind has not passed G0; else next event.
2. KV-R: repackage the three views with the frozen tool by content hash; one dry gen of kv3_hg_v1 and one hgi type on D11 before the switch.
3. Lever 2 items 1-2 on the first pilot.

### Lever 7. S81 SerDes (11 types)

Fix. S81-SERDES-R2: H3p to CTS census, then route; it is the only sign-off form (H2 leaves one relay hop at -57.76). Every SerDes kit generated
before 02cb43ff45e takes main's `serdes_boot_release_local.tcl`. G family: encoder-stage cohorts with tap rows near d0 (2387, 473),
d1 (2315, 592), d2-4 (2289, 673), d5 (2254, 704), CRC (2227, 607). J family: move rm toward the east face or add an rd.q -> bout_coll stage.
S81-DIE-R2 owns the G and J plan rows.

### Lever 8. bksel and IFN0 HW

- bksel (FABLE-FIX-S81-BKSEL): eco2 result decides. If DRT fails again, read the route_rc 2 cause of the first run before a third; the plan
  itself (213 HB4, target +10, no repair_design) is right. The 138 pins on g_bank[3] are one macro: a g_lat-style stage on that input bus
  is the structural form if the ECO cannot route.
- IFN0 HW (FABLE-FIX-S81-IFN0-HW): trunk reseat CTS read u_c0 p99-p1 118 -> 52, clk_regs 143 -> 35. Routed proof on hw_reseat2 is in GRT.
  Pass = TT >= -42 with internal FF >= 0 (was -144.3). HE needs one endpoint at -0.21: one HB4.

## 3. Stop list

1. col-wave1 volume, or any col DRT, before the h9_r1 congestion and h9_r2 DRT-0255 causes are named.
2. Routing h10_r0_p1-form kits with NOFIT groups; more rm2 / rm4 runs (site class is known).
3. Leaf kits (t47, t75, t8fix first) on GPL overflow 0.10; density, TD-off and keep-resize pilots; form B kits before the GPL rule; a second
   XR stage on all 75; stations or cycles for the t47 "2,538 um" path.
4. Any cb kit on S4Q3B / S4Q3C / S4Q6D sources or S4q9l2 rows; longer GRT hold caps; a uniform hold guard; RTL or CA / K changes for the cb
   lockup; tighter tol or per-pair budgets for the 707 residual pairs.
5. Clock rows cut from GRT readout spread on any die, KV rows C included, once an exact readout exists.
6. HEAD: t-pass setup repair on hw4, hw4e1, a second host_w rebuild, sd9A / sd9B / Form C retime, restarting sd9c GRT for the one tap gcell,
   four-net rip reruns (DRT-0255, no evidence).
7. G3 CTS or route on the current encoder placement; uniform 117 um tap re-pitch as the G3 fix; J5.
8. bksel: wire re-land tries, the Codex sibling ECO (fx_repair and allow-setup after the rip selection), sign-off from it.
9. A second hold ECO on the HW half before the trunk reseat routed read.
10. Still valid from 21:00: hold cells on the 27 KV landing-core pairs; +1 K row on io_serdes_2; quoting FF hold from the repair table.

## 4. Not checked

- The h9_r1 GRT report and the h9_r2 DRT-0255 net: I read the route log tails only. The root cause in lever 1 is INFERENCE.
- KV and HEAD exact tap spread: lever 2 on those dies is INFERENCE from the QC measurement and the reported window sizes.
- Why the first bksel hold-only ECO ended route_rc 2.
- ov25 CTS reads (t47 / t75), H3p CTS, sd9c GRT rem_q, hw_reseat2 routed, HG2c bind / LATCHECK, s5f strict rebind (prove PASS under 27
  defines at 20:56; BIND_RC 2 and CHAIN_CA_RC 4 in the log are from the earlier run), NF15c real3 die STA: all still running at 21:15.
- S81 "other flow error 7", QC "other flow error 7": not opened. Renders were not opened by me.
