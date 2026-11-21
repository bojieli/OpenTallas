# OPUS-FIX-KV-PV-R4 handoff (KV pv family owner: kv3_pv*, pv_pair; successor of OPUS-FIX-KV-PV-R3)

Written 2026-11-20 20:5x PST. Posts lanes/posts/OPUS-FIX-KV-PV-R4.md. D27 rows: lanes/handoff/OPUS-FIX-KV-PV-R4-d27-rows.json (posted to KV-PLAN-R2 20:4x).
Lane dirs: intel1 /srv/opentallas-scratch2/claude/opus-fix-kv-pv-r4 (repo = lane clone, tools/trace.py + run_trace.sh + run_pgc.sh, out/pgc_v8p/ABS-CENSUS.tsv),
epyc7 same path (repo = lane clone used for the push, cone tools+rtl+physical/common_flow; t/ test copy). Hub ~/tmp/okpvr4 (chain_tr.sh, chain_pgc.sh, watch_r4.sh, logs).

## Done
- ctl_cmd q[31] 1,228 um: NOT a real leg. dly_spread measures each chain when it is placed; q[31] (plan-sited relay_site, 2 loads = heads of
  pd8 t_10 / pd9 t_11 pad trunks) was measured before those trunks were spread. Placed v8p 3_place (intel1 opus-fix-kv-pv-r3/rleg/v8p_geom.tsv):
  q[31] (72.5,1345.9) -> INV _34_ (163.0) -> pd9 sg0 (222.2) / pd8 sg0 (294.3): 222 um. plan_geom_census on por_v8p: no ctl_cmd bin row on v8.
  The in-pass OT_DLY_SPREAD WORST lines (astk bin q[112..116] stages 1) are probably the same stale class.
- main c0feb4c70e: dly_spread prints OT_DLY_SPREAD FINAL max_hop ... on final sites (report only, gate unchanged, test F). Read it on D27 kits.
- plan_geom_census on por_v8p (16 pv types): 499 HOP rows > 300 um, worst 506 um kv3_pv_v2n; kv3_pv_v8 14 rows (389-408 um, 405-era stations).

## Running / open
- v8q (v8p plan on main 95661471cd): R3 hub chain ~/tmp/okpvr3/chain_q.sh (pid 4151714); GEN admitted on epyc7 ~20:1x PST, then kit to route
  (log ~/tmp/okpvr3/kit_v8q.log). My watcher ~/tmp/okpvr4/watch_r4.sh (pid 1198987) posts its key lines + v8m/v8c GRT_IT5_OVERFLOW every 15 min,
  exits when the chain ends; ot-wait 4151714 -> ~/tmp/okpvr4/wait_v8q.out. Read: 3_5 OT_DLY_SPREAD FINAL? (v8q tools predate c0feb4c70e: no FINAL
  line), place wns (3_detailed_place.rpt "wns max"), long hops (census tools/run_hops2.sh of R3 on a copy of 3_place.odb).
- v8m (flip) / v8c (control) on epyc7 fable-fix-kv-pv-r2/kit: still in 4_1_cts tap balance at 20:4x (over 7 h). cts_final wns -8,760 / -8,474 ps
  (placement RC). Flip decision = GRT it5 overflow v8m < v8c. Proof kits (DO_NOT_COUNT): not cancelled under the >3 h rule (proofs exempt).
- trace job (intel1, chain_tr.sh) queued on admission: confirms the q[31] neighbours on 3_5; optional.
- u_bin reset rows: RESET-RELAY-GEN-R3 had not posted by 20:4x; fallback rows in the D27 file.
- After D27 applies: station_route_spread on pv_v12's first placed D27 kit; one pv representative to CTS/route/sign-off, then siblings; export
  signed to AGIdock + rtx-pro ~/signed-export-1114. No sign-off or export from this lane yet.

## Update 2026-11-20 20:4x PST (read first)
- COORD ruled the 405-era re-site into D27: lanes/handoff/OPUS-FIX-KV-PV-R4-resite-rows.json (355 rows, 10 types, supersedes the R3 fault rows;
  per-type hops before/after and +cycles in the post). Made by epyc7 opus-fix-kv-pv-r4/srs_all.sh + agg.py (outputs srs/*.rows.json, *.report.json).
  v6n, v8, v12: no D25e3 placed geom; run srs_all-style on their first D27 placed kit.
- Waits armed (my Claude session background tasks; script hub ~/tmp/okpvr4/wait_ev.sh TAG KIT REPORT PID, 10-min polls): v8m congestion-5.rpt
  (client 2907386), v8c (2906217), v8q 3_detailed_place.rpt (client 1593537, kit launched 04:27 UTC). Watcher watch_r4.sh also posts.

## Update 2026-11-20 22:5x PST
- v8m (flip) DIED post-CTS: FAIL_POSTCTS FF structural hold -598 ps / 9,098 endpoints; TT setup after repair -1,847 (v8c -1,910). No GRT it5 from v8m:
  flip NOT READY. v8c wait + v8q place wait still armed. KV plan lane is now KV-PLAN-R3 (post.sh redirects).

## Update 2026-11-20 23:xx PST (COORD ruling)
- Flip OUT of D27 (no measured gain). D28 structural fix posted: lanes/handoff/OPUS-FIX-KV-PV-R4-D28-split.md (every pv type over the 400k
  cap; family split <v>w = g0+g2, <v>e = g1+g3, cut x 1080, +2 cycles on every pv input lane).
- v8c NOT cancelled by me (started by FABLE-FIX-KV-PV-R2; lane rule: never signal what you did not start). Asked COORD to cancel unit
  oth-ubuntu-1801628-1795205288. My v8c wait will then end with CLIENT_ENDED.

## Update 2026-11-21 0x PST: D28 split proof (COORD: prove on v3)
- Pairing: all 16 D27 bound_b3 binds pair T0Q*={g0,g2} (b/b_d1), T1Q*={g1,g3} (b_d2/b_d3) (epyc8 opus-fix-kv-pv-r4/pairing2.py). Posted.
- v8q place: WNS -492 ps, TNS -419k, floorplan non-tap 415k. v8c cancelled by COORD (its wait ended CLIENT_ENDED).
- Private tree epyc8 /srv/opentallas-scratch2/claude/opus-fix-kv-pv-r4/split28/tree (hardlink copy of kv-plan-r2/d27/tree, plan fac662d8c549).
  split28/prep.py moves the 2 v3 straddling windows west and writes spec.json; split.sh N runs type_split into qwen_kvsys/por_split_N.
  por_split_6 = RC_SPLIT 0, now installed as plan_of_record (base kept as plan_of_record.base_d27). Split plan ead4fa55edcd:
  kv3_pv_v3 (w: g0+g2) + kv3_pv_v3e (g1+g3), 11 cut buses/lanes, 9 lanes' fixed cycles changed (report.json).
- split28/straddle_1080.json: every pv type has 1-4 windows/rings across x 1080 -> D28 must move them (no lattice cut avoids them).
- type_split extension: epyc7 lane clone branch claude/opus-fix-kv-pv-r4-tsplit b461211ea7 (tests pass), NOT pushed yet: push after the bind
  is green. The private tree tools carry the same patch (+ spec drops clock.reserved_sites_um for re-derivation).
- Strict bind + LATCHECK: split28/bind.sh 1 -> split28/bindgate_1/gate.out (ot-run epyc8, client log intel2 ~/tmp/okpvr4/split_bind1.log).
- Next: on green, gen one half (kv3_pv_v3e or v3) with kv-plan-r3/proofs/proof_kit.sh-style script pointed at split28/tree -> CTS; read
  OT_CELL_CENSUS stage=cts + OT_CTS_POST_TIMING (post-hook) setup/hold; post to KV-PLAN-R3.

## CODEX notes 11-21 02:40 PST

- Split #2 strict failed RC_BIND 2, missing cut-only path L2267 stalled nine old lanes. Base-bind census PASS 28 transit rows, 8 intra, zero unplaced. Split #3 adds 28 lanes, plan f5fc6017c718, strict/LATCHECK epyc8 oth-ubuntu-2186169-1795256714, split28/bindgate_3/gate.out. Earlier compose8 launch RC1 was just missing exact bind output in the private base package; resumed against original D27 bind_of_record.
- Full cut inspection flagged cl_i_vport_E_N_vo at 0.43 μm from its new west-piece E boundary. Split9 fixes the macro clearance by moving unchanged core from x993.6 to x976.32 (17.71 μm channel). New candidate split28/tree/physical/die_plan/qwen_kvsys/por_split_9. Split #3 remains diagnostic for the nine missing lanes; proceed with split9 only after controlled bind and visual review. Cut remains 9,131 bits/39 ports over 1,521 μm using M4/M6 pin pairs. Keep tail-trunk site repair f2e64e5d3b in the eventual physical kit; exact prior PV v2 detour was the stale dly_spread helper.
- v8m flip FAIL -598 FF, v8p flip+pad FAIL -554.47 FF (10,953 endpoints), v8c control cancelled per prior ruling. D28 remains the structural fix and uses no flip.

## STAND-DOWN 2026-11-21 ~06:xx PST (read first; successor OPUS-FIX-KV-PV-R5)
### In flight
- chain11 (epyc8, ot-run from intel2, lane OPUS-FIX-KV-PV-R4; client log intel2 ~/tmp/okpvr4/chain11.log):
  split28/chain11.sh = compose11.py (Codex split 10 + ring cl_i_vport_E_N_vo_d2 moved to (967.68, 241.92) so it sits in w with its
  N 989-1039 bus window) -> por_split_11_composed -> COPY installed as tree plan_of_record (old one kept as por_split_10_installed)
  -> r8_ev.json = bindgate_4/r8pin2.json (re-derived on the split) -> bind.sh 5 = strict bind + LATCHECK + BPC -> split28/bindgate_5/gate.out.
  Re-arm: `ssh intel2 'ot-wait <unit>'` (unit: `grep oth- ~/tmp/okpvr4/chain11.log`), or read bindgate_5/gate.out when ALL_DONE appears.
- Accept rule: diff bind_report errors vs the base with `python3 -I split28/errdiff.py split28/basebind/bind_report.json
  <tree POR>/bind_of_record/bind_report.json`. The 45 base errors (30 R8_STALE hub_Wo astk, 14 EMIT, 1 PARAM_REGEN) are inherited from
  D27b6 (KV-PLAN fixes them in D27c); new = 0 means the split is bind-clean.
### Next (brief items)
1. On bind 5 new=0: gen + CTS of the w half kv3_pv_v3 via split28/proof_kit.sh kv3_pv_v3 cts (ot-run on epyc8, --priority proof, OT_LANE).
   Read OT_CELL_CENSUS stage=cts + OT_CTS_POST_TIMING (post-hook) setup/hold; post to KV-PLAN-R5 (KV-PLAN-R3/R4 stood down).
   G0 cell budget (split 9/10): v3 275k place / 157k synth, v3e 269k / 155k, both TARGET.
2. After placement: station_route_spread on the placed w half (FABLE-VISUAL-0030 cause 1, the 2,411 um owner_response_data bundle).
3. Push the type_split extension: epyc7 lane clone /srv/opentallas-scratch2/claude/opus-fix-kv-pv-r4/repo, branch
   claude/opus-fix-kv-pv-r4-tsplit b461211ea7 (relay keys, collector_root_xy, wavefront_min_depth, column-swap core moves; tests pass)
   via ot-push-main once bind 5 is clean. Also add: a fail-closed check that a landing ring core sits in its bus piece.
### D28 pv rows / rules learned (for KV-PLAN-R5)
- Form: <v> (keep name, w = g0+g2) + <v>e (g1+g3), cut x 1080, g1<->g2 column swap (core_moves; final-position overlap check).
- Pairing confirmed on all 16 binds (T0Q*={0,2}, T1Q*={1,3}).
- Needs census (type_split census on a base bind_latency) + lane_reference (split_lane_reference_export.py on the base) or the bind fails.
- Port windows and rings across x 1080 on every pv type: split28/straddle_1080.json. Moved windows must not overlap their neighbours
  (G0 abutment + face density errors); Codex split 10 shows the right shifts for v3 (L2279/L2393 mine, plus L2289/L2366 west).
- START relay tx pin cland_rstart_out must sit next to the cut (v3: (993.6, 756)), or the cland_relay hop is 545 um.
- Reset: RESET-RELAY-GEN-R3 two-pass rows for pv_v3/v3n/v7 are sign-off-capable (hop 290/282/269 um, 0 unplaced, tap_check clean),
  and are re-derived on the split plan (D28).
- clock.reserved_sites_um is dropped by the split for re-derivation.
### Cancels (owner rule >3 h + over cap)
- Cancelled: v8f oth-ubuntu-4168642-1795149806 and v8g oth-ubuntu-1559719-1795153886 (epyc10; 539k at CTS, -13,454 / -1,223 ps,
  structural: unbuffered pad-trunk stage hop), v8q oth-ubuntu-197469-1795235234 (epyc7; 415k at floorplan, place -492). Watcher
  watch_r4.sh stopped. kv3_pv_v8 disposition posted: HOLD, carried by the D28 split.
- Remaining (not mine): 11 autopilot ot-job wave kits on epyc8 (10) + epyc9 (1), units oth-ubuntu-37xxxxx/2835944-179524883x.
### Shared-tree warning
Codex ran split 8-10 + bind 3 + G0 in split28 under this lane name 02:2x-03:3x. Bind 3 (RED, sink x 2143.8) was likely corrupted by
my plan_of_record swap mid-run. Never swap plan_of_record while another bind or G0 is using the tree: check `ps` for split28 first.
- UPDATE: chain11 unit oth-ubuntu-1403789-1795268325 ENDED rc 1 at COMPOSE (nothing installed; tree plan_of_record is still the split 10 copy,
  plan 086a50a08e27, with its bind-4 bind_of_record). Error: "type_split: FAIL kv3_pv_v3: pin fclk_out_ft0_o source_clock_port clk_t171
  is not a tap of the base type". The only change from Codex's compose10 is the ring core move cl_i_vport_E_N_vo_d2 -> (967.68, 241.92).
  Codex hit this same class in split 10 (por_split_10_basetap_attempt) and solved it in compose10_with_separate_base.py. Read that script's
  handling of clk_t171 / base taps first. Leftover dirs por_split_11_input / por_split_11_composed: remove with ot-delete, or reuse a new number.
  Then rerun chain11.sh (make it take fresh dir names), or apply the ring move another way.
