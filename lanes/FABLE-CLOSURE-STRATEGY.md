# FABLE-CLOSURE-STRATEGY 2026-11-15 21:15 PST: the gate RC under-read is on QC too (same-path proof), C3b passed, seven levers, stop list

Read-only review by FABLE-CLOSURE-2115. Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: the 19:15 strategy; FABLE-PD-KV-1945 / QC-S4q7ef / HEAD-NF13 / S81CORES-1915 / QCHOLD-1915 / S81-1750; rulings
r199-r224; queue posts to 21:25; `failure_breakdown.py` 21:10.
Measured by me (21:20-21:30 PST): every wave kit on epyc2/7/8/9/10 + intel1 with a log younger than 30 h (277 kits, 204
types, HBM excluded): TT setup at the gate (`postcts_gate_tt.json`), `OT_PG_*` keys in `config.mk`, route log class, and
TT setup in `signoff/signoff.json`; the worst setup path of one QC kit at the gate and at sign-off. JSON and log text only,
no database opened, no STA run. The scan script was run from my session and is not in the repo.
MEASURED = read or computed by me. REPORTED = lane post or Fable review. INFERENCE is marked.

`failure_breakdown.py` 21:10: S81 41/394 types (62/64 cores), HEAD 19/26, QC 7/127, KV 5/56.

## 0. What changed since 19:15, and which 19:15 levers landed

| 19:15 lever | state 21:25 |
|---|---|
| 1 S81 col Event F2 | NOT landed. F2a compose started 20:2x. The 118 ps loss is explained (routed RC, r222). col3_c view still not in the r2 kits: pvf57acd2b routed again at DRC 276 (21:05). |
| 2 S81 G3b | B6gG3 gated 20:43 (bind 0, LATCHECK 873/873). 16 svc types held: synthesis pilot FAILED again (canonicalize 125 min, 4,792 per-bit writes). Merge fix in test. |
| 3 `DRT-0255` | Die phase PROVEN (p_t49 DRC 0; hd_ctl, hd_spn past iteration 1) and live on 7 HEAD types. C3b PASSED iteration 1 at 21:20 (56,402 -> 11,772, 0 x `DRT-0255`). C3b is NOT yet in any gen env. Variant B also failed. |
| 4 KV | Tree c1 rebuilt 21:19 (one sha, gates pass). Ring split v20 bindable but 27 rings > 340 um; v21 in bind. pv depths merged (r224). q2 cause measured. win1 view built, kit GRT running. |
| 5 QC events | No adopt posted for S4q6d / S4q7e / S4q7g. Hold stall class closed as stale (r211). |
| 6 Die route closed views | Refusal approved (r209). hd_tile at 717.12 is already signed (15:22); the die kit still reads the 708.48 view. |
| 7 HEAD types | private leaf merged (r215); no routed hd_serdes sign-off. |
| 8 Cores | Diagnosed (r212): bksel = unrepaired slew, gunit = repair outside the clock freeze. ECOs not finished. |

New since 19:15, MEASURED by me:

1. **The gate under-reads setup on QC as well, and on the same path.** sle_hc2__cl9c4c4509__clf60c5152 (S3R attempt_3,
   epyc10, routed DRC 0): gate +2.48, sign-off -178.75. Same start and end point in both reports
   (`u_u_xl2_4.g_t[1]...g_c[0].f` -> `u_u_xl2_4.q_bad`). Lever 1.
2. **Two HEAD types failed `DRT-0255` on NF13a and were relaunched unchanged at 21:05.** hd_st_n3_turn: internal ring net
   `u_cland_u1_i/u_ring.dch[5].u_dsel/net21745`. hd_host_n: face pin `h_tx_ft_i[23]`. Neither is on the die-phase list.
3. **QC: 8 more `DRT-0255` stops in 2.5 h**, all with `OT_PG_TRACK_TRUTH=1` and `OT_PG_CELL_KEEPOUT=0` only (coll_n,
   slw_hc2, sle_fe_v3, sle_hc0, sle_hc2, slw_stm_v3, sle_stm_v2, sle_sc_v1). Latest kit per QC type: 13 `DRT-0255`.

## 1. Levers. Not dispatched first

| # | dies | lever | unblocks | owner | dispatched |
|---|---|---|---|---|---|
| 1 | QC, S81, KV | Signal-net RC for the gate and for TT repair on ALL dies, not only the 6 S81 r2 kits; QC hc fan-out tree | QC hc / fe families after C3b; S81 col 216 | GENBUG-IMPL; DIE-QC-103 + QC-HC-STRIP-1115 | NO (r222 covers S81 r2 only) |
| 2 | QC, HEAD, S81 | C3b into the gen env now; class per type (face pin = die phase, internal pair row = C3b); stop unchanged relaunches | 13 QC types + 2 HEAD + S81 leaf t54; 46 slice_station + 11 serdes at launch | GENBUG-IMPL, KIT-OPS-5, DRT0255-PROOF-1115 | PARTLY (r214 item 3 conditional; HEAD hd_st_n3_turn / hd_host_n not) |
| 3 | S81 | col: stations on the 1 mm edge chains inside F2, not in a later delta | 216 types | DIE-S81-92, S81-TAPROWS, S81-COLABS-1115 | PARTLY (r222 item 2 says "next col delta") |
| 4 | HEAD | Register the signed hd_tile 717.12 record as the die-kit closed view, after one check of its hold and slew | 144 MY die-route units | HEAD-100, CORE-ROWS-1115, KIT-OPS-5 | NO (found 21:4x by KIT-OPS-5) |
| 5 | KV | Ring split v21 only; pv D=4 with firm sites; q2 M3 strips; win1 view by kit GRT | 51 types | KV-102, KV-HGSPLIT-1115, KV-PVGEN, KV-Q2-CLK-1115, KV-ABSPIN-1115 | YES (r216, r224) |
| 6 | QC | S4q6d -> S4q7e -> S4q7g; cross-tap hold guard on core taps only | about 72 held types | DIE-QC-103, QC-SRC-CLOSE-1115 | YES (r207, r211) |
| 7 | S81 | svc per-bit write merge; bksel slew ECO; gunit ECO inside the clock freeze | 16 types, 2 cores | GENBUG-IMPL, S81-CORES-1115 | YES (r212, r214) |

### Lever 1. Gate RC under-read is cross-die (NOT dispatched)

Evidence (MEASURED), gate TT setup -> sign-off TT setup, every routed kit with a sign-off in the last 30 h:

| family | kits | gate -> sign-off | loss |
|---|---|---|---|
| S81 col_h9_r2 (clce45cab5) | 6 | -139..-149 -> -267..-369 | 118 to 226 |
| S81 col_h9_r2 (older tree) | 3 | -328..-338 -> -465..-510 | 137 to 171 |
| QC sle_hc2 | 1 | +2.5 -> -178.8 | 181 |
| QC sle_fe_v1 | 1 | +50.9 -> -60.6 | 111 |
| QC slw_su_l0 | 2 | +78.4 -> +36.1; +56.9 -> +36.2 | 42; 21 |
| QC sle_su_l0, sle_fw_v3 | 3 | -4.3 -> -7.6; +8.5 -> +9.1; +50.7 -> +53.1 | 3; 0; 0 |
| KV kv3_io_ft_v1 | 1 | -22.5 -> -62.7 | 40 |
| S81 slice_station | 13 | -70..+186 -> -50..+173 (t22 -69.9 -> -49.9) | median 12, worst 48, best -20 |
| HEAD (ctl_e, mesh_e, eshim_tx, st_n4, tile, turn_a) | 8 | +60..+206 -> +52..+198 | 8 to -2 |

sle_hc2 path, the same cells at the gate (`postcts_gate_TT.log`) and at sign-off (`signoff/tt/sta.log`), kit
epyc10 `.../qwen_compute/s29q103S3R/items/sle_hc2__cl9c4c4509__clf60c5152/attempt_3/gen/...`:
- Data arrival 1,043.9 -> 1,221.0 (+177). Capture clock 1,065.0 -> 1,065.2. Launch clock 250.4 -> 242.8. The clock is
  not the cause.
- Net capacitance, gate -> routed, per stage (fF): 21.9 -> 29.7, 21.2 -> 27.2, 11.9 -> 15.8, 14.3 -> 20.9, 32.7 -> 42.8,
  11.0 -> 17.2, 8.8 -> 15.0. That is +29 % to +71 % on every multi-fan-out net of the path. These are ordinary nets with
  4 to 10 loads, not one long M7 run.
- The first five stages are a fan-out tree of one flop: BUFx2 (8 loads, slew 152) -> INVx1 (8 loads, slew 239) -> BUFx2 ->
  BUFx10 -> BUFx2 (10 loads, 42.8 fF, slew 172). They cost 518 of the 978 ps data delay at sign-off (406 at the gate).
- The kit has no `OT_TT_SETUP_REPAIR` key; the late ECO ran once for 11,218 s and was exhausted (494 endpoints, slew 465).

Root cause: `setRC_rcx.tcl` under-reads routed signal capacitance by 30-70 % wherever nets are dense or long. Families
with short, low-fan-out nets (HEAD, slice_station, su_l0) do not show it. Second effect, INFERENCE: the TT repair that is
default since 18:14 runs on the same RC. On sle_hc2 it sees +2.5 and has nothing to repair, so it cannot close what
sign-off will show. The calibration is therefore the precondition of the TT repair on every die.

Fix:
1. GENBUG-IMPL: do the r222 item 1 fit on signal nets from the routed SPEF of sle_hc2 attempt_3, sle_fe_v1__cl8210183c
   attempt_3 (both epyc10 / wave S3R) and kv3_io_ft_v1 attempt_24, together with the 6 r2 kits. One RC set per layer for
   signal nets, for all dies. Accept test: predicted minus sign-off within 30 ps on these 9 kits.
2. Until it lands: read QC hc / fe / stm, S81 col and KV io kits at sign-off only. A gate pass on these families is
   not a prediction.
3. DIE-QC-103 with QC-HC-STRIP-1115: the `g_flat.g_lv[*].g_c[*].f` select flops of `u_u_xl2_*` drive about 40 loads through
   x1 / x2 cells. Either replicate the flop per load group in RTL (4 copies, no latency change), or give the hc kits
   `repair_design` with a fan-out limit before GRT. Decide on the count of such flops in the 494 failing endpoints
   (not read by me: only the worst path).
4. Do not relaunch the late ECO on sle_hc2 S3R: -179 over 494 endpoints is not ECO range.

### Lever 2. DRT-0255: put the proven forms in, by class (partly dispatched)

Evidence: REPORTED DRT0255-PROOF 21:20: C3b on slice_station t37 passed iteration 1 with 0 x `DRT-0255`; GRT overflow 0
on every layer, usage 6.93 -> 7.30 %, M6 guide length in pair rows 86,675 -> 1,966 um. Die phase: p_t49 DRC 0.
MEASURED: section 0 items 2 and 3; the `config.mk` of every HEAD NF13a kit I read (hd_host_n a1 / a2, hd_st_n3_turn
a1 / a2, hd_host_e a1 / a2, hd_mesh a6, hd_st_k5, hd_host_w) carries no `OT_PG_*` key at all.

Root cause: two classes, one form each. Face pins on the core PG phase -> die phase. Pins and guides inside internal
M6 pair rows -> C3b capacity cut. A type can have both.

Fix:
1. GENBUG-IMPL: C3b (`pg_pair_cap.tcl`, sourced last in `grt_pre.tcl`; keys in the 21:20 post) into the gen env of QC,
   S81, HEAD and KV now. The condition of r214 item 3 is met.
2. KIT-OPS-5: hd_st_n3_turn = C3b (ring `u_dsel` net, internal). hd_host_n = die phase (face pin). Their a2 kits of
   21:05 are unchanged and will stop the same way.
3. KIT-OPS-5 / DRT0255-PROOF: KIT-OPS-5 reports the die-phase keys in `spec.json`; they are not in `config.mk`. Confirm
   on hd_ctl a2 that the floorplan log shows the die-phase offset (8.448) before more types are added.
4. First QC kits: slw_hc2 and sle_sc_v1. Read GRT overflow on the first hc kit (hc is the congested family; t37 used
   7 %). Then read sign-off, not the gate (lever 1): C3b removes the route stop, it does not close hc2.
5. S81: the 46 slice_station and 11 serdes types launch on G3 with C3b from the first kit.

### Lever 3. S81 col: stations inside F2 (partly dispatched)

Evidence (MEASURED): table above; all six r2 kits also carry sign-off TT hold -4.7 to -123.1 (non-port) and 211-433
slew violations. REPORTED (DIE-S81-92 21:3x): worst sign-off path `u_u_n23 -> u_bout_frame_int_o0/q[130]`, about 22
buffers and 1 mm along the bottom edge, 327 fF routed against 191 fF estimated; per-port window gives back at most 79 ps.

Root cause: a 1 mm combinational run in one 833 ps cycle. Arithmetic: -267..-369 at sign-off plus 79 from the window
is -188..-290. No window, view or repair setting closes that.

Fix:
1. DIE-S81-92: put the station rows for the bottom-edge chains (`u_bout_frame_int_o0` and its siblings) into F2a / F2b
   itself, one flop row per 340 um of run, with the lane latency change in the same event. A pilot without them
   will read about -190 or worse at sign-off and costs one more round.
2. S81-TAPROWS: list every col path over 600 um between flops from one routed r2 DEF, so the station set is complete
   in one event (the worst path is one of a family).
3. S81-COLABS-1115: col3_c view cd64688b278c into the F2 kits (DRC 276 = 2 x 138 is unchanged at 21:05).
4. KIT-OPS-5: r222 item 3 (TT repair at GRT ran on FF libs only on these kits).

### Lever 4. HEAD die route: use the signed hd_tile (NOT dispatched)

Evidence: REPORTED KIT-OPS-5 21:4x: hd_tile attempt 3 (NF6 key, DIE_AREA 717.12 x 1036.8) was signed 15:22; the die
kit still reads the 708.48 view. hd_st_n4 NF13a route running since 20:08. MEASURED: the `signoff.json` in the wave
kit dir of hd_tile NF6 attempt_3 (age 9.9 h) reads TT setup +52.0, TT hold non-port -16.47, 1,168 slew violations;
hd_st_n4 NF6 attempt_10 reads TT +81.7, hold -9.41 (port class).

Fix: HEAD-100 / CORE-ROWS-1115: register the signed 717.12 record as the closed view and re-prepare the 144 MY units.
Before that, one read: if the registered record is the kit I scanned, its non-port TT hold -16.47 and the slew count go
into 264 instances; if the signed record is a later ECO directory, register that one. No rebuild of hd_tile.

### Lever 5. KV (dispatched)

Evidence (REPORTED): v20 ring split: G0 0 errors, strict bind 0, LATCHECK 2404/2404, all types under 400k, but ring
displacement median 117 um, p90 739, max 1,000, 27 rings over 340 um. v21: median 19, max 390, in bind. pv legs
(placed read): F2 max 2,297 um, F4 max 1,396 -> D = 4; F1 max 988 -> D = 3. q2: SRAM edge 30 nm above the M2 track,
M3 via enclosure 16 nm from the OBS (rule 18). win1 view: pin gcells with 0 free M4 623 -> 3, M5 623 -> 165.

Fix: KV-102 adopts v21, not v20 (a ring 340-1,000 um from its band is 1-3 unplanned hops per ring lane). If v21
fails bind, v20 only with a station row for each of the 27 rings. KV-PVGEN: no pv kit before the `lp_even` firm sites
exist (the D = 4 flops are named, not sited). KV-Q2-CLK: persistent M3 strips on both edges of both bottom SRAMs.
KV-ABSPIN: row only if head-core GRT markers drop in the running kit pair.

### Lever 6. QC plan events and hold (dispatched)

Evidence (REPORTED): S4q6d / S4q7e ADOPT-OK; S4q7g = S4q7f + 48 + 24 pad sinks. The pre-GRT cross-tap hold guard skips
all 84 taps, so routed kits end at non-port FF hold -10 / -20. MEASURED: sle_fw_v3 S3R sign-off TT hold non-port
-12.59, sle_su_l0__cl7a55c676 -38.96, sle_hc2 -8.53: the guard fault is visible on three routed kits.

Fix: unchanged from r207 / r211. Order: adopt S4q6d, then S4q7e, then S4q7g. QC-SRC-CLOSE: the guard branch (core taps
only) before the first C3b kits route, or they arrive at sign-off with the same -10 to -40 hold.

### Lever 7. S81 svc and cores (dispatched)

svc: REPORTED 20:49 pilot FAIL, cause confirmed (4,792 per-bit writes: pvq 2,120, land 1,232, pmem 512, hold 512, fq
416). No svc kit before the `bind_native_glue.py` write-port merge. bksel: slew repair ECO on b1o (183 of 215 failing
paths have a pin over the 320 ps limit). gunit: same ECO without `core_final_repair.tcl`. MEASURED: the 21:08 line on
gunit reads TT -16.44 and "fails setup_tt"; the blocking limit is -42, so the open item on gunit is hold only.

## 2. Stop list (technical dead ends)

1. Variant C2, variant B (M4 / M8 obstructions over M6 stripes) and the cell keep-out: all failed in iteration 1.
2. Unchanged relaunch of a `DRT-0255` type: hd_host_n a2, hd_st_n3_turn a2, the 13 QC types.
3. A gate pass as a sign-off prediction on QC hc / fe / stm, S81 col, KV io (loss 40 to 226 ps).
4. TT repair as the cure while it runs on the uncalibrated RC (it sees +2.5 on sle_hc2).
5. Late ECO on kits at -110 or worse over hundreds of endpoints (sle_hc2: 11,218 s, exhausted).
6. S81 col: per-port window, col3_c view or repair settings as the closing step (at most 79 ps against -267..-369);
   more r2 kits on the current tree (DRC 276 each).
7. KV: v20 as the final ring split; blanket OBS cut or pinwire views; moving the SRAM on the q2 DB; re-route without strips.
8. QC: extra hold-repair passes; S4q7f as bound; cb relaunches on S4Q2 / S4Q3C.
9. HEAD: rebuilding hd_tile (it is signed at 717.12); place_lines / windows-mirror; hd_serdes READY on GRT RC.
10. S81: svc synthesis reruns before the write merge; bksel re-floor or new CTS; a fourth gunit ECO with
    `core_final_repair.tcl` in the chain.

## 3. Not checked

- sle_hc2: only the worst path was read; the share of the 494 endpoints that sit behind the same fan-out tree is unknown.
  sle_fe_v1 (-111) path not opened. Routed capacitance by layer not decoded (SPEF not parsed).
- Whether the HEAD die-phase keys reach the PDN step: `config.mk` has none; `spec.json` and the floorplan log not read.
- Whether the signed hd_tile record is the kit I scanned.
- C3b: no DRC 0 yet (iteration 2 running); no C3b kit on a QC hc type exists.
- v21 bind result, S4q6d / S4q7e / S4q7g adopt state, F2a compose result, win1 kit GRT: none posted by 21:25.
- Station count and lane latency cost of the col edge chains: not derived.
