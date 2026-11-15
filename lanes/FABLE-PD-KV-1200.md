# FABLE-PD-KV-1200: kvgeom7v review, 7u / 7r status, pv and ring-band rows, ectl 37/26 cores, io_cor DRT-0255, pc_v1 (2026-11-15 12:55 PST)

Read-only review. Technical PD only. MEASURED = read by me today from a plan, gate output, log or report. REPORTED = from a
lane post. INFERENCE = my reasoning. I ran no build, no STA, no bind and opened no database: plan JSON reads on epyc7,
log / signoff-report reads on intel2 and epyc9. Nothing launched, stopped or changed.

## 0. Answers

1. **7v is not ready, but not because of the ectl rows.** Phase 1 is clean (G0 0 errors, LATCHECK 2404/2404). Phase 2
   failed at 20:1x UTC: `RC_BIND2 1`, 8 errors, 65 types instead of 56, no bound top, so no LATCHECK2. All 8 errors are on
   pc types (4 R8_STRAP_PAD, 3 TYPE_SPLIT, 1 EMIT inventory); none names an hg type or krsp / rq. 7v was gated with the old
   table recipe `run_gate_kv7r8.sh` (r8.py pads); 7u, 7tb and 7q pass with `run_gate_kv7pin.sh` (derive + pin). Rerun 7v
   with the pin recipe; that is the only missing step on the plan side.
2. **7u is done**: plan b7156937f334, pinned bind 0 errors (160 / 56 / 2545 / 429530), LATCHECK4 2404/2404, G0_4 PASS,
   R8_RECHECK 0. It can post now. 7v = 7u + 202 leaves (8 hg station lists, 64 lanes, 192 latency rows, note).
3. **7r does not bind** on the pin recipe: `R8_STALE pvw_1__u_s0_b0.bcx[0:5] <- pvw_1__u_ctl.cmd` as-built 55, bound 70,
   table 63. The reset tap is no longer the blocker (G0 PASS on 2917c8322ddf). The blocker is the +7 on ctl_cmd against a
   table that pins 91 members to shipped values. It is the alignment item KV-PVGEN listed as (3).
4. **pv rows and ring-band rows are in no plan.** 7u, 7v and 7h have 0 `core_link_pipe`, 0 `SELREP32`, 0 `RESET_PIN`,
   0 band_spread 1.5. That is the right place for pv (own delta after 7v). For the ring bands the 1.5 row is the wrong
   lever, see 5.
5. **band_spread 1.5 is not enough, and may be a step back.** All 328 KV ring bands already carry
   `band_spread_target 7.0`; io_cor ft19_i has actual spread 7.01 and is the band that died with DRT-0255. Band area is
   not what boxes the pin.
6. **The ectl hold is structural on q2, a normal ECO item on q1.** q2 has two clock leaves 70-95 ps later than their
   neighbours; data padding is at its limit there. And the m10 ECO did not repair anything: it was a no-op on both cores.

## 1. Measured

### 1a. Plan gates (epyc7 `kv-102/kvgeom7/`, 20:2x-20:5x UTC)

| variant | plan sha | phase 1 | phase 2 recipe | phase 2 result |
|---|---|---|---|---|
| 7u | b7156937f334 | G0 PASS, LATCHECK 2404/2404 | pin | BIND4 0 errors, LATCHECK4 2404/2404, G0_4 PASS |
| 7tb | c6b392413fbd | same | pin | BIND4 0 errors, LATCHECK4 PASS, G0_4 PASS |
| 7q | eec05af44e52 | same | pin | second try BIND4 0 errors, LATCHECK4 PASS |
| 7r | 2917c8322ddf | G0 PASS, no bound top | pin | BIND4 R8_STALE pvw ctl.cmd 70 vs 63, no LATCHECK |
| 7v | 685e18352c8e | G0 PASS, LATCHECK 2404/2404 | r8 pads | BIND2 8 errors, 65 types, no LATCHECK2; G0_2 running |
| 7h | on disk 20:19 UTC | not gated | - | differs from 7v in 21 types (19 hg/hgi, hroot, hub_C) |

- 7v bind errors (`out2_kvgeom7v/bind/bind.log` l.434-442): R8_STRAP_PAD on kv3_pc_v1__cl7f648944 (pad 45 and 32 over
  capacity 15) and kv3_pc_v3 (62 over 26); TYPE_SPLIT kv3_pc_v1__cl4ea58a5c 8 instances as 3 variants,
  cl7f648944 12 as 7, pc_v3 4 as 2; then "EMIT clock landing: emitted module/type inventory changed".
- 7v rows (same on all 8 hg types): rq 3 stations, 39 bits, as 7m. krsp 4 rows, one per core, 5 stations each, bits
  512 / 768 / 768 / 512; hops <= 374 um, last station to core pin 140-151 um on q0 / q1. Lanes: 32 at +3, 32 at +5.
- Station load of the krsp rows (computed from the rows): all 4 rows share (306,468) = 2,560 flops at one point;
  q0 + q1 share (306,740), (306,1010), (306,1216) = 1,280 each; q2 + q3 share (605,543) = 1,280.
- The handoff states G0 does not check the hops to `rsp_data` (no core_conns sidecar for ectl). So G0 PASS says nothing
  about the last hop.

### 1b. ectl 37/26 cores (intel2 `kv-ectlk-rl-cores37/q1,q2/signoff`, `kv-ectlk-rl-eco/q1_m10,q2_m10`)

| | q1 | q2 |
|---|---|---|
| TT setup | +226.18 | +221.08 |
| FF hold (overlay) | -3.02, 1 endpoint | -20.21, 60 endpoints |
| FF insertion min / max / spread | 161.1 / 217.8 / 56.8 | 162.2 / 284.5 / 122.3 |
| TT insertion spread | 60.4 | 133.9 (max 336.3) |
| pair skew FF worst / p99 | 60.9 / 47.4 | 121.4 / 90.2 |
| worst pair | flop to flop | rd2[160] to SRAM g_macro[0], SRAM to row1[94] |
| TT max slew (limit 320) | 486 worst, data pins | 497 worst, data pins `u_c...u_qd/q[*]/D`, row1, rd2 |
| TT max cap | none | SRAM `g_macro[1].u_s/rd_out[181]` 57.3 over 46.1, 4 pins listed |
| OCV 5 % hold (info) | -18.7 | -43.8 |

- q2 worst hold path (`signoff/ff/sta.log`): `u_a.rsd_o[194]` -> `u_b.rd2[194]`. Launch leaf clkbuf_leaf_193, stage
  53.7 ps, clock at 190.2. Capture leaf clkbuf_leaf_192, stage 125.0 ps, clock at 284.1. Skew 94 ps. The data path
  already holds 6 hold buffers (hold9688, 7679, 9689, 9690, 7680, 9691) and one inverter, and is still -20.21.
- q2 removal path: `u_rpin.rst_n` (leaf_245, 173.5) -> `x2_o[6]` (clkbuf_leaf_191, stage 125.2 ps, clock 283.5):
  -11.82, with hold8027 / hold8028 already in it.
- Leaf stage delays seen in the reports: q2 FF 125.2 (leaf_191), 125.0 (leaf_192), others 30-54; q2 TT 140.4 (leaf_191),
  85.4 (leaf_202). q1 FF 29-50. So q2 has two or three slow leaves; q1 has none.
- q1 worst hold path: `rd2[399]` -> `rd3[399]`, one inverter, launch clock 166.2, capture 192.9 (leaf_96, 9.9 ps of
  leaf wire). 27 ps of skew, 25 ps uncertainty, -3.02. Plain short path.
- The kit lineage of q2 says the same thing: the signed q2 came from a seven-instance LVT clock fix ("CLK PASS TT 76.49
  / FF 77.03, all 9852 pairs", SOURCE_STATUS.txt) plus a targeted BUFx6f buffer pass (KV60_TARGETED.txt) and a CTS
  database copied from the lineage root (CTS_ID_NOTE.txt). The 37/26 rebuild ran a fresh CTS at 10:28 and has 121 / 132.
- **ECO m10 was a no-op** (`q1_m10`, `q2_m10`, ended 11:59 PST, exit 5):
  - `config.mk` last override wins: q2 l.119 and q1 l.83 set `POST_GLOBAL_ROUTE_TCL = /work/grt_post_core.tcl` after
    the `eco_post.tcl` line. The log shows `source /work/grt_post_core.tcl`; `prd_hook.tcl` never ran. No `OT_PRD`
    line, no repair line in `run_prd.log`.
  - Components 27,842 before and after. Global route: "Routed nets: 0". Detail route re-ran to 0 violations.
  - Then `CLK_GEOM_DIFF FAIL: clk_freeze_pre.tsv missing (ot_clk_freeze never ran in the ECO)`, route_rc 5.
  - Both ran on intel2 itself (ot-run chose localhost: the kit dir exists on no build host).

### 1c. Ring bands and DRT-0255

- Plan 7v: 328 bands, every one `band_spread_target 7.0`, `ring_place ff`. Actual spread: io_cor ft19_i 7.01,
  i_host_fdi 2.92; hroot i_kvs_ctl_o_hroot_Q 6.18; hgi_v2 i_ectl_Q_N_tN 2.26. Resize notes are dated 11-08, before the
  11-13 io_cor failure.
- `clock_landing_plan.py` l.1046: `band_spread` is legal only for 1 < S <= 4 and sizes band area = S x reserve.
  `landing_placement.tcl` l.155: column form fills bit-major upward within a column.
- REPORTED (TYPES-KV-FAIL 10:5x): the boxed pin is QN of a FIRM DFFLQNx1 in a column with zero vertical gap, an AND2x2
  abutting its right edge, M2 PDN rails every 0.54 um. REPORTED (FABLE-CLOSURE 11:55): all 49 recent routes have
  OT_PG_CELL_KEEPOUT 0 and no OT_PG_DIE_PHASE. Not all KV DRT-0255 are ring nets (sys_SD / sys_c clock leaf nets,
  io_ft_v1, io_cor_v1 strap net).

### 1d. kv3_pc_v1__cl4ea58a5c attempt 17 (COORD add-on; epyc9 `attempt_17/geom/auto_geom.json`, 3_place, kvgeom6)

- 322,551 cells, 70,333 flops, 12 macros (4 pcc 293.8 x 267.8, 4 pcf, 4 SRAM), macro area 27.1 %, fill of free 0.0426,
  empty 0.783. GRT did not finish in 600 s.
- Taps: 36 grid taps in `nearest` mode, 7 to 9,181 sinks (t4 9,181, t10 7,189, t7 6,934, t1 6,083, t34 5,377, t31
  4,248, t5 3,431). The kit sets `OT_TAP_MAX_SINKS = 1200`. 8 taps on a macro (clk_t4 at 517.9, 570.3). 20 sinks stay
  on root `clk`; leg 2,182 um from driver (172.3, 190.1) to sink (1028.8, 1515.9).
- r2r 1,609.6 um, 16,320 of 63,578 captures over 405 um; worst `u_cland_i_kvs_emb_px_tok` ring dsel -> `u_bin_...eq`.
  relay_collapse 82. col_v 6.44 at (550, 1007.5), channel_v 3.11 at x 543-552: the gap between the pcc pair.
- pin_reg_p90 202.7 um (limit 30), 2 unregistered pins (cone deeper than 6 cells).
- Attempts 13-16 are autocleaned to logs only. The plan row for this type is identical in 7v and 7h, and the 7v bind
  splits its 8 instances into 3 variants.

## 2. Levers, ranked

| # | lever | evidence | owner |
|---|---|---|---|
| 1 | Post 7u now. Rerun 7v phase 2 with `run_gate_kv7pin.sh kvgeom7v` (tree with the rtl37 overlay exists). Retire `run_gate_kv7r8.sh` | 7u all green; 7v 8 errors all on pc types from the pads recipe, 0 on hg | KV-102 die owner |
| 2 | q2: fix the clock, then pad. Rebuild q2 CTS with the leaf rule that the signed lineage needed (split or upsize leaf_191 / 192 / 202, SRAM clock pins on their own short leaves), target pair skew <= 80. Do not stack more hold buffers on a 94 ps skew | leaf stage 125 vs 30-54 ps; pair skew 121 FF / 132 TT vs 77 on the signed q2; 6 buffers already in the worst path | KV-ECTLK-RL |
| 3 | Fix the ECO kit before any relaunch: one `POST_GLOBAL_ROUTE_TCL` (eco_post.tcl) as the last line, clk_freeze pre-dump present, and check the log for `OT_PRD` lines and a changed component count. Stage the kit to a build host | m10 inserted 0 cells on q1 and q2; ran on intel2 | KV-ECTLK-RL |
| 4 | q1: after lever 3 the same ECO is enough (1 endpoint, -3.02, one inverter path). The slew list (486 worst, data pins) is a repair_design item in the same pass | q1 FF skew 61, no slow leaf | KV-ECTLK-RL |
| 5 | Check q0 / q3 on the same three numbers when they finish (leaf stage max, pair skew, insertion spread) before any ECO | q2 only shows it at sign-off | KV-ECTLK-RL |
| 6 | krsp rows: spread the shared first station. 2,560 flops at (306,468) and 1,280 at four more points need a declared box, not a point; measure the last hop to `rsp_data` on the first placed hg kit (G0 does not) | computed from 7v rows; handoff note | KV-102, KV-ECTLK-RL |
| 7 | io_cor DRT-0255: drop the band_spread 1.5 row. Order: (a) one io_cor route with the PG flags of DRT0255-PROOF; (b) if the ring pin still fails, change the FIRM column pattern in `landing_placement.tcl` (one free row or site between flops on the QN side, or pin-stretched form), which is a generator rule for all ring_ff bands | all bands already at 7.0; ft19_i at 7.01 failed; column fill has zero gap | DRT0255-PROOF-1115 (a), TYPES-KV-FAIL-1115 (b), DIE-KV-ROUTE-1 for the die-level ring check |
| 8 | pv as its own delta after 7v, one event: 7r stations + core_link_pipe D3 + SELREP32 + ctl_cmd / bc alignment (+3 on every pv2 source) + kv_pv_col_regen + pv_join_t RESET_PIN (16 types, HCPARAM-ALL). Derive the pin table for that event; do not pin ctl.cmd to the shipped value | 7r R8_STALE 70 vs 63; branch red on 4 selrep tests; 0 pv rows in 7u / 7v / 7h | KV-PVGEN (rows, tests), KV-102 (event) |
| 9 | pc_v1: stop the wave on kvgeom6 for this type. Needs, in one pc delta: placement regions for the 17 contents so logic does not fall into the 69 um gap between the pcc cores; tap assignment that honours the 1,200 sink limit (nearest mode ignores it) and no grid tap on a macro; station rows for the ring-read -> bin class (16,320 captures, same class as hroot) | fill 0.043, taps to 9,181, r2r 1,610 um, GRT unfinished; attempt 17 | TYPES-KV-FAIL-1115 (family listing on attempt 17 placed DB before autoclean), KV-102 (rows) |
| 10 | pc TYPE_SPLIT: cl4ea58a5c binds as 3 variants and cl7f648944 as 7 under the pads table. Confirm on the pin recipe that the count is 56 types before any pc kit is generated from 7v | bind.log l.439-441 | KV-102 |

## 3. Stop list

1. No more waiting on the current 7v phase 2: it has failed. No re-run of `run_gate_kv7r8.sh` on any 7 variant.
2. No relaunch of the m10 ECO on q1 / q2 with the same config.mk, and no second pass counted as "ECO did not converge":
   it never ran.
3. No further hold-buffer or margin pass on q2 before the clock leaves are fixed; no hold margin or uncertainty change.
4. No ectl ECO or route on intel2.
5. No band_spread 1.5 row in 7v or 7tb; no wider band as the DRT-0255 fix; no unchanged io_cor relaunch.
6. No pv rows merged into 7v; no 7r re-gate against the pinned table; no pv_v1n station copy to the other 15 pv types.
7. No attempt 18+ of kv3_pc_v1__cl4ea58a5c on kvgeom6 (attempt_18 already exists); no density or GRT-time setting as the
   fix.
8. Still in force: FABLE-PD-KV-0945 stop list 1-7, FABLE-CLOSURE 11:55 stop list (no port-hold pads).

## 4. Not checked

- 7v on the pin recipe (not run by anyone yet); G0_2 of 7v still running at 20:5x UTC; nothing of 7h beyond a diff.
- The 19 reg-start / 41 port-start split of q2 (REPORTED by KV-ECTLK-RL); I read the two worst paths and the pair-skew
  table only, not all 60 endpoints. Fanout and wire of leaf_191 / 192 / 202 (my netlist parse failed); the cause of
  the slow leaves is INFERENCE from the stage delays and the SRAM pair.
- Whether the signed 36/25 q2 view still has pair skew 77 (read from a kit note, not a signoff record).
- q0 and q3 (still running). Whether the 37/26 pin geometry equals the views attached in 7v.
- How the column form uses the spread value for the vertical gap (read 3 lines of the script, not the proc);
  whether the 11-13 io_cor kit had spread 7.0 (inferred from the 11-08 resize note).
- pc_v1: cell positions (I read metrics, not the database or the image); why attempts 4-16 failed; the cause of
  TYPE_SPLIT.
- Any ps number for the krsp +5 path; DIE-KV-ROUTE-1 state.
