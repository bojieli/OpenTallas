# FABLE-CLOSURE-STRATEGY 2026-11-15 11:55 PST: seven levers, three new route-stage classes, stop list

Read-only review by FABLE-CLOSURE-1130. Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: the 09:3x strategy, FABLE-PD-S81-1045 / T14-0935 / HEAD-0945 / KV-0945 / QC-0945 / QC-SUC-0800, r131, the queue from
07:10 to 11:45, `failure_breakdown.py` (11:18), and on the build hosts: route logs, `5_route_drc.rpt`, `config.mk` and
macro LEFs of the kits named below. MEASURED = read or computed by me today. REPORTED = from a lane post. INFERENCE is marked.
I ran no STA, no route and no database read; only log, report, LEF and netlist text.

`failure_breakdown.py` 11:18, technical rows: S81 types 36/394 (52 running, 24 held for the event); HEAD 19/26 (7 running);
QC 3/127 (59 running, 51 held, 3 flow error, 3 kit input); KV 5/56 (28 held, 20 running). The tool lists no congestion,
DRC or timing class on the four dies. The classes below come from the route logs and DRC reports, which it does not read.

## 0. What landed since 09:3x, and what is new

Landed or moving (no new lever needed, not repeated below):
- M8 grant: B6gE deletes `type_m8_grant.types`, so every S81 type below the M8 ceiling gets M8 again (was 12 of 68 kits).
- S81 type merge, tap rows, E2 stations: in B6gE; the open items are r131 Events F and G.
- HEAD clock sites: NF8 hd_tile built and gated on the stamped tree. Unit u201 with 16 boxes + tap snap + `obs.tcl` drop:
  486 / 2 / 2 / 1 / 1 over steps 0-4 (REPORTED, DIE-ROUTE-ABS-1 10:5x). 8-thread 12-step rerun is running.
- QC: S4Q3B adopted (15 cb types), n9 `sta_region` views registered, su_c rows in S4q4c, sc rows drafted (9 types, 34 rows).
- KV: band2col on all 37 other types (1,129 bands widened), placed scan merged as a post-place check.
- Non-port hold repair is the default on main since 07:22 (flow-lateeco).

New, measured today, not in r131 or any Fable report:
1. The PG keep-out that fixes `DRT-0255` is off on every routed kit and has never been proven by a route (lever 1).
2. Every routed col_h9_r2 kit ends flat at 276 `Lef58EolKeepOut` markers on one hard core abstract (lever 2).
3. The S81 `DRT-0073` types fail on a core clock pin sealed under a full M6 obstruction (lever 3).
4. Six seam reset forms were tried; each moves the failure between recovery and removal (lever 4).

## 1. Levers, ranked by types unblocked

| # | dies | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | QC, S81, HEAD, KV | `DRT-0255`: turn the PG keep-out + die phase on, prove it by a finished route, split the residue by mechanism | 77 route failures on about 50 types in two days (QC 34, S81 26, HEAD 12, KV 5); 20 of 49 routes of the last 25 h | KIT-OPS-5 (env), NEW LANE DRT0255-PROOF (probe + proof routes), KV-102 (ring spread rows) |
| 2 | S81 | `ot_v41_bf_col3_c` abstract: 64 M5 pins end on their own wire emitted as obstruction; 276 fixed markers per type | all 216 col types (552 markers on h10_r1) | GENBUG-IMPL (abstract generator), DIE-S81-92 (view into Event F) |
| 3 | S81 | `dsfd_coll_lane_{e,w}_safe8_ntf`: interior M5 clock pin under full M4-M6 obstruction, no access point | 3 lep types failed today; every type that uses this view | GENBUG-IMPL (same generator rule), DIE-S81-92 |
| 4 | S81 | Seam / relay reset: key the last reset stage to the capture clock tap; half-cycle landing if a pad is not enough | all 216 col types (Event F gate) | S81-SEAM-RST-1115, DIE-S81-92 |
| 5 | QC | Families still in no delta: fe (9 types), hc0 / hc1 density, st_b logic path | fe 9, hc about 6 named kits, st_b 11 | QC-FWST or NEW LANE QC-FE-ROWS, DIE-QC-103 |
| 6 | KV | hg / hgi: station rows from the 10:01 family listing; no pads for the output-port hold | 19 hg / hgi types + hroot | KV-102, KV-ECTLK-RL |
| 7 | HEAD, then S81, QC, KV | Die clock sites: finish the u201 proof, then give QC a row file (none exists) | HEAD die DRC; one avoided re-key of QC types | DIE-ROUTE-ABS-1, CLKSITE-RESERVE-1115, DIE-QC-103 |

### Lever 1. DRT-0255 and the PG keep-out that is not running

Evidence (MEASURED):
- `FAILED` lines 11-14 and 11-15: 77 `DRT-0255` of 733 failures. By die: QC 34, S81 26, HEAD 12, KV 5. About 50 distinct
  types. 09:00-11:15 today: 9 (QC st_b five variants, sle_fe_v1, coll_s; HEAD hd_spn).
- Route logs younger than 25 h on epyc8 / epyc9 / epyc10: 49 kits. 20 ended with `DRT-0255`, all in the 1st optimization
  iteration, after iteration 0 left 12,732 to 118,445 violations. The kits that pass end iteration 0-4 at 0.
- All 49 have `OT_PG_CELL_KEEPOUT = 0` (or no line) and no `OT_PG_DIE_PHASE`. Search of all kit `config.mk` on six hosts:
  2 kits have the keep-out on, both QC, both still at placement. No kit has the die phase on.
- PG-AWARE-1 proof set on intel2 (`pg-aware-1/proof`, 12 kits with the keep-out on): none has a `5_2_route.log`. They
  stopped in place, CTS or GRT on 11-14. The fix merged at 21:13 on 11-14, the all-die env was reverted at 00:25, and the
  only evidence is "cells under crossings 1,773-3,993 -> 0". No route has ever shown it removes the error.
- Two different types fail in the same box: sle_st_b_v2 pv41c959f3 and slw_st_b_v1 pv6ace3e48 at (38.76, 381.90). So
  the st_b cause is fixed geometry of the family, not a random repair cell.
- hd_spn: `b_i[67]` is an M7 pin at (181.664, 0.096) whose access point (182.624, 10.830) has no path; `b_i[66]` is an
  M5 pin 8 nm beside it on the same face.
- REPORTED mechanisms: (a) M7 face pin on an M7 PG track (PG-AWARE-1: 186-1,696 pin boxes per kit); (b) cell under an
  M5 x M6 PG crossing; (c) ring band flops in a zero-gap FIRM column with logic abutted (TYPES-KV-FAIL, io_cor);
  (d) SRAM pairs abutted on pin faces (HEAD host_w, mesh).

Root cause: four mechanisms share one error text. Fixes for (a), (b) and (c) exist in the tree; none is enabled in the
wave and none has a finished route behind it. The class has had no owner since the 23:5x limit killed the proof set.

Fix:
1. NEW LANE DRT0255-PROOF: run `pga_probe.tcl` (PG-AWARE-1, read-only, about 10 min each via ot-run) on the kept
   `5_1_grt.odb` of today's 20 failed kits and post the count per mechanism (a) to (d). The databases are in the kit dirs.
2. Same lane, in parallel: restart 6 proof routes from GRT with `OT_PG_CELL_KEEPOUT=1 OT_PG_DIE_PHASE=1
   OT_PG_TRACK_TRUTH=1`: sle_st_b_v2, coll_s, sle_fe_v1 (QC), leaf t54 or t25 (S81), hd_spn (HEAD), io_cor (KV). The die
   phase needs a floorplan restart; the keep-out a GRT restart. Pass = route past iteration 1 with no `DRT-0255`.
3. KIT-OPS-5: on the first pass, put the three flags back into `die_gen_env` of all four dies for new kits. The events
   B6gE, S4q4c and 7u regenerate nearly every type; they should not regenerate with the flags off.
4. KV-102: the ring `band_spread` 1.5 rows (TYPES-KV-FAIL READY-ROWS) go into 7u. QC has the same ring nets failing
   (`u_cland_b_hw_ctl_hc3_i/u_ring.dch[*].u_dsel` on st_b, `u_cland_l9_eo_l9_wi_i` on fe_v1): DIE-QC-103 takes the
   same row form for the st_b and fe ring bands once the probe confirms mechanism (c) there. INFERENCE until then.

### Lever 2. col3_c abstract: 276 EolKeepOut markers on every col route

Evidence (MEASURED, epyc10 and epyc9 wave tree `s81/7073a6b4a59`):
- Five routed col_h9_r2 kits (clce45cab5 pv2833ee2b / pv843b0fff / pva8c07948, clb8d86cd5 pvb2cd22a7 / pvf0595d0f) ran all
  65 iterations: 104,461 -> 17,335 -> ... -> 360 -> 276, then 276 unchanged from about iteration 15 to 64. Final reports
  276, 276, 276, 277, 277.
- All 276 are `Lef58EolKeepOut` on M5, between `u_u_e13w.u_view.u_c` or `u_u_e13e.u_view.u_c` (138 each) and its own
  pin nets (`pval`, `prow`, `pnseg`, `pseg`, `ppos`, `pv`, `perr`, `qy`). All sit at y = macro bottom + 0.084.
- The master is `ot_v41_bf_col3_c` (LEF of 11-14 04:21). Pin `pval[0]`: M5 `RECT 151.968 0 151.992 0.084`. The same
  track continues as obstruction: `OBS M5 149.088 0.084 149.112 0.131` and so on (20,726 M5 obstruction rectangles, the
  real wires). 64 of the 65 M5 pins abut an obstruction of the same width at the pin end. 64 pins x 2 corners = 128,
  plus 10 with a 0.047 extension = 138 per instance. The count matches exactly.
- Every col family kit has the e13 view with `u_view.u_c` and `pval` connected (h9_r0_p1 / p4 / p5 / p6, h9_r1, h9_r2,
  h10_r0, h10_r2: 2 instances; h10_r1: 4). No other col family has reached route yet.

Root cause: the abstract generator cuts the pin at 84 nm and writes the rest of the same wire as obstruction. The router
sees a pin end touching foreign metal, so the marker is in the view, not in the routing. No number of iterations removes it.

Fix:
1. GENBUG-IMPL: in the abstract generator, a wire that continues a pin on the same layer and track is pin geometry (one
   PORT rectangle to the wire end), or is dropped from OBS. Regenerate the col3_c view. No layout change, no re-route of
   the core.
2. Proof: re-run detail route of one r2 kit from `5_1_grt.odb` with the new LEF. Pass = 0 at about iteration 15.
3. DIE-S81-92: put the view into Event F. Without it all 216 col types fail DRC 0 after the reset fix lands.
4. Same scan on the other masters. My scan (`/tmp/fc1130_pinobs.py` on epyc10, 59 LEFs of the S81 wave tree) finds the
   same pin-abuts-own-obstruction pattern on 13 more: `ot_s81sl_ve_m_tpl` (M5 875), `vs` (1,334), `vq_tpl` (299),
   `vsw_tpl` (388), `ve_s_tpl_w1728` (100), `vn_a_tpl`, `vn_b_tpl`, `ot_dsrom_su_hcpost_lane_pr` (81), and M4 only on
   `cfg7_seq`, `cfg7_seq_bfp`, `capc5r`, `su_t_rxsb`, `cfifo_crs4`. INFERENCE: whether they give markers depends on the
   pin being connected and on the M4 rule; no leaf route finished in the window to check. Check the first one that does.

### Lever 3. coll_lane view: clock pin with no access point

Evidence (MEASURED): `DRT-0073 No access point for u_bound.u_u_ln0/ck[0]` on dsdv_slice_lepe_nh_mus_LP__t1 (07:12),
lepw_mus_LP__t2 (09:56), lepe_mu_LP__t2 (10:14). LEF `dsfd_coll_lane_e_safe8_ntf` (295.92 x 444.96): pin `ck[0]` is M5
`RECT 147.924 236.232 147.972 236.76`, in the middle of the core. Obstruction on M4, M5 and M6 is one rectangle each,
(4.32, 0)-(295.92, 444.96). A via from M6 down to the pin lands on obstruction, so the pin cannot be reached.

Root cause: the signed view covers M1-M6 fully and leaves no window over an interior pin. Not a routing or PG issue.

Fix: GENBUG-IMPL, same generator pass as lever 2: for an interior pin, cut the obstruction of the layer above over the
pin (one via landing plus enclosure) and of the access layer along one track to it, or export `ck[0]` as an M6 / M7 pin.
Then the tap of the parent lands on it. Rule for both levers: every signal pin of an abstract must have one legal access
point with the abstract's own obstructions; check it at view registration (pin access on a one-macro design, 1 minute).
The three types are held for `defparam LOCAL` today; release them only with the new view.

### Lever 4. S81 seam and relay reset: tap-keyed last stage

Evidence (REPORTED, S81-SEAM-RST-1115 11:05 and 11:42, TL-COLH9R0P6 10:25; col_h9_r0_p6 `4_cts.odb`, 8,380-8,573 async pins):

| form | recovery fails / worst ps | removal fails / worst ps |
|---|---|---|
| before | 4,369 / -745 | 286 / -264 |
| pa replicate by regex | 376 / -326 | 465 / -229 |
| pc replicate grid 300 um | 423 / -328 | 352 / -180 |
| pc2 grid 300 + one copy per sink instance | 0 / +104 | 579 / -238 |
| pd registered per chunk + async slice | 170 / -600 | 242 / -203 |
| pe sync registered clear | 393 / -324 | 373 / -418 |
| pf pe + grid 300 | 0 / +44 | 993 / -380 |

- TL-COLH9R0P6: the reset chain is launched on tap t24 (clock at 11 ps); the capture flop on t11 is clocked at 294 ps.
  Removal -223 ps with recovery +584 ps on the same pin. The insertion difference between taps of one type is 283 ps.

Root cause: the reset is the one signal that crosses clock taps without a station. A copy placed by grid or by sink
instance still gets whatever tap CTS gives it. Late capture tap: removal fails. Early capture tap: recovery fails. The
worst numbers of every form are about the tap-to-tap insertion difference (180-420 ps), not wire length.

Fix (INFERENCE, arithmetic on the numbers above; S81-SEAM-RST runs the same `ac5.tcl` on it):
1. Split first: for the 579 removal fails of pc2, print launch tap and capture tap (`report_checks -format full_clock`).
   If they differ on nearly all, the next two steps apply. 10 minutes.
2. Form T: one reset copy per capture clock tap, with the copy's clock pin bound to that tap (the kit has
   `tap_pair_affinity.tcl` / `tap_chain_affinity.tcl`; key = sink tap, not grid cell). Copy to sink is then same-tap:
   recovery has 833 ps minus the local wire; removal needs clock-to-Q + wire >= 57 ps (25 uncertainty + 32 removal), so
   one fixed delay cell per copy if short. The cross-tap step moves to the copy's D pin, an ordinary data path with
   283 ps of skew: a hold pad on one net per copy.
3. Form N, if the D-pin pad is too large: clock the copy on the falling edge of its capture tap and take its input one
   chain stage later (cycle-neutral, needs the `tb_ot_pl_seam` miter and bind_reset). Copy to sink then has 416 ps for
   recovery and +416 ps of removal margin; the cross-tap step tolerates about -240 to +560 ps of tap difference.
   Measured difference 283 ps fits. This is the lockup form the owner approved for seam hold on 10-27.
4. Gate unchanged: recovery and removal >= 0 at CTS on one h9 and one h10 type, then Event F.

### Lever 5. QC families in no delta

Evidence:
- fe (9 types): REPORTED (QC-0945) sle_fe_v1 has 7,686 zero-logic bits over 405 um; no delta carries rows. MEASURED today:
  sle_fe_v1 cl8210183c failed route twice (07:02 `DRT-0206`, 10:42 `DRT-0255` on a `u_cland_l9_eo_l9_wi_i` ring net).
- hc0 / hc1: MEASURED (wave lines 11:05, 11:16) sle_hc1 cl7d360508 376,325 cells on 439,910 um2 soft area (0.86 per um2,
  rule C asks x2.04 or a split in 3); sle_hc0 cl05696ed1 347,989 on 446,106 (0.78, x1.86). GRT congestion `GRT-0116` today
  on slw_hc1 cl68f9248e (07:32) and sle_hc1 cl22c1ff36 (07:42). sle_hc2 cl9c4c4509 variants: 112,125-118,445 violations
  after iteration 0, then `DRT-0255`. QC-0945 cleared the hc placed WNS; it did not look at density.
- st_b / fw / stm post-CTS stop: 6 kits 06:30-07:33 with pin-register mean 260-266 ps (S4C event, before the rows).
  Covered by S4fw4b / S4q4c if it binds (REPORTED 0945: `PARAM_REGEN W5`; not re-read by me).

Fix:
1. QC-SC-ROWS-1115 runs its generator on the fe family next (same placed-dump method, 790 um hops on sc), or a NEW LANE
   QC-FE-ROWS does. Rows into S4q4c or the delta after it.
2. DIE-QC-103: hc0 and hc1 need area or a split, not a retry. Check the free area beside each hc partition in S4Q3B;
   where the die has it, grow the soft area to the rule C figure in S4q4c. Outline growth is pre-approved.
3. Do not relaunch hc / st_b / fe route before lever 1 step 2 has a result for QC.

### Lever 6. KV hg / hgi: stations, and no pads for the port hold

Evidence:
- REPORTED (KV-102 10:01, kv3_hg_v1 placed): 189 path families, no stations at all (`ot_relay_mid_stations.txt` empty);
  `u_hstN_tN -> u_headN_eN` 3,000 endpoints over 1,327 um; `u_astk ep` 2,580 endpoints over 288 um.
- REPORTED (TYPES-KV-FAIL 11:2x, OpenSTA on `4_cts.odb`): hgi_v3 3,537 hold endpoints, 3,463 of them to output ports;
  hroot 1,942 of 1,950; hgi_v2 1,362 of 1,516. All -34 to -40 ps. Required 177.5 ps = virtual clock 250 + 12.5 - 85;
  arrival 137-144 ps. One internal family: `u_hstN_tN.u_reg.ti_b -> u_headN_eN g_front`, 10 endpoints, -29.8 ps.
- MEASURED: hgi_v2 cl2862d491 stopped at 09:32 after 3 h of GRT hold repair (-196 ps, 1,780 endpoints).

Root cause: (setup) hg / hgi have one-cycle paths over 1.3 mm and no station rows. (hold) the 1,780-3,537 endpoints are
the output-port contract against an ideal virtual clock. They are port paths, which do not block sign-off, and the
in-flow repair of them is what stalled the kit.

Fix:
1. KV-102: station rows for the hg / hgi frames from `kv-102/hgv1fam/families.tsv`, `u_hst -> u_head` first, in the
   delta after 7u, with KV-ECTLK-RL's krsp +5 cores. This is the open half of the 09:3x lever 4.
2. Do not add `hold_hb4` rows on the 26 ft output buses for the port contract. Check that the hgi and hroot kits are
   generated from a tree with flow-lateeco (non-port hold repair); the stalled kit predates it or opted out. The seam
   hold is judged at die STA on real views.
3. The 10 internal endpoints at -29.8 ps are a normal hold ECO.

### Lever 7. Die clock sites

Evidence (REPORTED, DIE-ROUTE-ABS-1 10:5x): with 16 boxes, tap terminals snapped to M8 / M9 track points and the
GRT-only obstructions dropped, u201 goes 486 / 2 / 2 / 1 / 1; the 19 M8 min-step markers were off-track tap terminals
(8 and 24 nm off). Memory 12.2 GB at 8 threads. Open: about 400 M8 pin-against-PG markers, unassigned; 1 residue marker.
QC-0945: no QC delta has a clock-site row. KV-0945: 437 of 32,856 KV clock cells are in a declared island.

Fix: as r131 and HEAD-0945; three additions.
1. The 400 M8 pin-against-PG markers need an owner now: DIE-ROUTE-ABS-1 names the pins and the PG shapes on u201 (one
   report), then HEAD-100 moves the pins or trims the strap. It is the next floor after the 12-step run.
2. `--snap-tap-pins` is a generator rule for all four die clock kits, not a HEAD unit setting.
3. CLKSITE-RESERVE-1115 delivers the QC row file against S4q4c before the 59 running QC types sign.

## 2. Stop list (technical dead ends)

1. Relaunching any type that died with `DRT-0255` unchanged. 20 of the last 49 routes repeat it at iteration 1.
2. More detail-route iterations or a late ECO on col types: the 276 markers are in the col3_c view (lever 2).
3. Routing the three lep types (and any type with a `safe8_ntf` lane view) before the view has a clock pin window.
4. More reset forms keyed by grid, regex or sink instance (pa, pc, pc2, pd, pe, pf). Six tried; the variable is the tap.
5. Timing repair on async reset nets: 350 ps gained in 250 iterations and still -183 (09:3x), and it cannot fix removal.
6. `hold_hb4` pads on KV output buses for the port hold contract, and in-flow hold repair on port paths.
7. Retrying QC hc0 / hc1 at 0.78-0.86 cells per um2, and cbn_q11 as built (FABLE-PD-QC-1115: 463 um one-cycle hop
   over rows with 0 horizontal capacity; setup -1,117 ps at CTS).
8. Snapping an existing die clock tree onto a site template (HEAD-0945: 1,326 stages over 405 um). Stamp one tree.
9. M8 as the fix for leaf y-slots (S81-1045: 12 of 13 screened types need vertical tracks; M8 is horizontal).
10. Kept from 09:3x: B6gslcf / B6gshcf, S4x / S4v2, KV 7m / 7n / 7g, bksel at virtual clock 975.

## 3. What I did not check

- The mechanism split of today's 20 `DRT-0255` kits (lever 1 step 1). The st_b and fe ring reading is INFERENCE.
- Whether the M4 / M5 pin pattern of lever 2 gives markers on the leaf cores. No leaf route finished in the window.
- S4q4c, 7u and B6gE bind / G0 / LATCHECK results: none was posted when I wrote this.
- The 8-thread 12-step u201 run: still running.
