# FABLE-PD-KV-1450: KV hg / hgi, the m7hg_g 6-h "no progress" and why the family does not close (2026-11-15 15:35 PST)

Read-only review, technical PD only. MEASURED = read by me today from the named log, report or config. REPORTED = from a
lane post or an earlier review. INFERENCE = my reasoning, not run. I ran no build and opened no database; nothing was
launched, stopped or edited. Kit: epyc7 `/srv/opentallas-scratch2/claude/type-kvhgi2/m7hg_g/kit` (host clock is UTC;
PST = UTC - 8). My parse of the congestion reports: `cg.py` in my scratchpad (not kept on the fleet).

## 0. Answers

1. **It was not a hold or timing repair loop.** `repair_timing` never started. The job was inside
   `global_route -end_incremental` (the reroute after `repair_design`), silent for 5 h 51 min with 1 of 8 cores busy.
   The watchdog metric "repair_Violations best 0 last 0 rows 15" is a false match: it read the 15 rows of the
   detailed-placement legalizer table (`Total Violations`, last row 0). MEASURED.
2. **Reading of the silent phase (INFERENCE, with measured support):** an overflow loop that cannot end. The residual
   overflow is 36-53 gcells, 49 of 53 inside head cores, most with capacity 0 or 1. Rip-up cannot clear a cell with
   capacity 0 and usage 1. In the full route of the same run the last iterations cost 14-17 min each for that residue;
   the incremental call prints no iteration lines. Not a hang (one busy core), not a memory problem (27.3 GB of 56).
3. **The kit itself is obsolete.** m7hg_g is kv3_hg on the kvgeom5-line netlist with the merged `ti_b` banks and no
   stations (CTS setup -753 ps, FABLE-KVOVF F1 and 11.2). It was kept "for the route answer only". It has given that
   answer (section 1c). There is no structural fix for this kit; do not assign one.
4. **Why hg / hgi does not close across attempts:** no hg / hgi kit has been built on a stationed plan yet. The wave is
   still on kvgeom6 (`kit_wave.json` event kvgeom6, plan `src_kv_kvgeom6_pgL`), and all 21 hg / hgi rows are held on
   `event_adopt:kvgeom7j` / `kvgeom7`. 7j was posted READY+ADOPT at 08:47, 7u passed its gates by 12:55; I find no 7u
   READY+ADOPT post and no wave switch. Every hg / hgi failure of the last two days is the old, unstationed block.
   MEASURED 14:4x PST.
5. **Not the cause** (MEASURED on m7hg_g): layer budget. Total usage 13.9 %; M8 is open and 2.43 % used, M7 5.07 %.
   No channel or face is short of tracks. The only 2D overflow outside a core is 4 cells at (491-508, 1305).
6. **Next real risk for kv3_hg is size and turnaround, not congestion:** 434,201 instances at CTS, 504,192 after
   `repair_design`; one GRT stage ran 15.5 h without reaching hold repair.

## 1. Measured on m7hg_g

### 1a. Timeline (log `run/logs/asap7/dp_kv3_hg/base/5_1_grt.tmp.log`, report mtimes, `NOPROG.tsv`)

| step | UTC | duration |
|---|---|---|
| start, read 4_cts.odb | 06:31 | |
| pin access | to 06:46 | 14 min (856 s) |
| `global_route -congestion_iterations 30 -allow_congestion`, pass 1: 15 iterations, then NDR dropped on 2 clock nets | to about 08:05 | about 1 h 20 |
| pass 2: 30 iterations (reports at iteration 5 / 10 / 15 / 20 / 25 / 30 = 08:27 / 08:49 / 09:20 / 10:33 / 11:56 / 13:07) | to 13:20 | 5 h 15; whole command 6 h 34 (23,643 s) |
| `repair_design -max_wire_length 120`: 47,312 long wires, 61,470 buffers, 8,097 slew | to 15:36 | 2 h 16 (8,155 s) |
| ft / cland hop repair at 110 um: 8,521 buffers on 8,507 nets | | 132 s |
| detailed placement (504,163 cells, max move 8.3 um) | to 15:40 | 77 s |
| `global_route -end_incremental`: first pass, then `GRT-0297` NDR dropped on `clknet_0_clk_t43` | 15:40 to 16:09 | 29 min |
| no log line | 16:09 to 22:00 | 5 h 51, cancelled; `cores_busy 1.0`, 27.3 GB |

- Iteration cost in pass 2: 4.4 min (5 to 10), 6 min (10 to 15), 15 min (15 to 20), 17 min (20 to 25), 14 min (25 to 30).
- Cells: 434,201 -> 495,671 -> 504,192 (+16 %). 339,694 nets; 14 % of them are over 120 um.
- The scope journal on epyc7 shows only the docker client (2.5 min CPU); the busy core is from the watchdog row.

### 1b. Overflow by iteration (congestion reports, 2D markers)

| report | markers | inside a head core, capacity 0 | inside, capacity 1-4 | outside a core |
|---|---|---|---|---|
| iteration 5 / 10 / 15 | 20,000 each (report limit) | - | - | - |
| iteration 20 | 416 | 226 | 18 | 172 |
| iteration 25 | 108 | - | - | - |
| iteration 30 | 36 | 9 | 24 | 3 |
| final | 53 | 16 | 33 | 4 |

Final congestion table: total 232 (M4 6, M5 20, M6 176, M7 30, M8 0); max 3 H / 2 V. 10 iterations and 2 h 47 min
(10:33 to 13:20) took the count from 416 to 36, and the final step put it back to 53.

### 1c. Where the 53 final markers are

| place | count | detail |
|---|---|---|
| north edge row of the e2 cores, y 552.6 (0.3 um inside head0_e2 and head1_e2) | 19 | vertical, capacity 0 or 1; nets `u_hst0_t2.ti_b[*]` and their repair nets |
| south edge of head0_e2, x 162.7-171.3, y 337-345 | 23 | vertical, capacity 3-4, usage +1; nets include `u_cland_i_slg_Q_N_krsp` ring `dch[7]`, `dch[15]` |
| head0_e2 column x 171.9, y 351-385 | 3 | horizontal, capacity 0 |
| core centre clk / rst_n pin cluster, y 124.5 (head0_e0 x 168.4, head1_e0 x 764.1-764.7) | 3 | horizontal, capacity 0; `net274613` is the same net FABLE-KVOVF named on attempt 14 |
| head1_e2 x 757, y 346 | 1 | horizontal, capacity 0 |
| below the ectl row, (491-508, 1305), between q1 and q2 | 4 | vertical, capacity 17-27, usage +1; `u_cland_i_astk..ctl_qo` ring nets and `q1_t0[*]`; also the 3 HOT marks of the layout review |

- Same netlist, control without the M7 close (kv3_hg attempt 14, REPORTED FABLE-KVOVF sec 4): 2 markers. With
  `OT_M7_CORE_CLOSE cores 16` here: 53, of which 19 on the e2 north pin row. On kv3_hgi_v2 the same close took 43 to 1
  (REPORTED). So the M7 close is not a family rule: it helps hgi_v2 and hurts kv3_hg. I did not check whether
  attempt 14 also had `OT_PG_TRACK_TRUTH` (here on: 6,194 obstructions, M7 derated 55.9 %).
- Layout review of this kit: `local_density 1.385`, 29,121 gcells over 90 %.

### 1d. Wave state for the family (`~/coord/autopilot/kit_wave.json`, 14:4x PST)

- `event kvgeom6`, `plan .../kw45/src_kv_kvgeom6_pgL/.../plan_c.json`, `src_sha 96f13b36a258`.
- 21 hg / hgi keys in `hold_items`; release conditions `event_adopt:kvgeom7j` (13), `event_adopt:kvgeom7` (6),
  `KV current event` (2).
- `die_gen_env` has no `OT_KEEP_WIRES`; no hg / hgi `item_env` has it. The automatic keep (`replica_keep.py`, main
  6f0c8e1765 and r140) is newer than the wave source tree.
- intel2 `~/OpenTallas/physical/common_flow/grt183_make.sh`: no `repair_antennas` in the allow-congestion wrapper
  (FABLE-KVOVF F2). The m7 form used `SKIP_ANTENNA_REPAIR = 1` instead. No `m7_core_close` file in `common_flow`.

## 2. What keeps the family from closing (ranked)

1. **The stationed plan has not reached a kit.** MEASURED 1d. The timing causes are known and measured (FABLE-KVOVF:
   merged `ti_b` banks; nine unstationed bus families of 0.75-2.1 mm on kv3_hg; kt / reset / start broadcasts on hgi).
   7j carries 40 stations on 13 buses for kv3_hg, the kt 2-stage rows, 152 reset terminals and the i_ectl station
   (REPORTED KV-102 08:47). None of it has been placed.
2. **kv3_hg is too large to iterate.** MEASURED 1a: 434k cells, 15.5 h in one stage. The owner-approved rule is to
   split types over 400k. 7j adds stations, so the count rises. INFERENCE: the other 7 hg frames are in the same range
   (not checked).
3. **Core-internal capacity-0 cells make every congestion pass run to its limit.** MEASURED 1b / 1c. With allow-congestion
   these markers do not block the flow; they only cost time: 2 h 47 for the last 10 iterations of the full route, and the
   whole silent incremental phase (INFERENCE).
4. **`OT_MAXWIRE_UM = 120` turns 47,312 nets into 61,470 buffers** (2 h 16, +16 % cells, and about a third of the nets
   re-routed incrementally). OpenROAD prints `RSZ-0065 max wire length less than 143u increases wire delays`. On 7j the
   station hops are up to 380 um, so this count does not fall by itself. MEASURED cost; the gain of a larger value is
   INFERENCE.
5. **Output-port hold in GRT.** REPORTED (TYPES-KV-FAIL 11:2x, wave 09:32): 34-40 ps short on every single-stage
   output-port flop against the ideal virtual clock; hgi_v2 stalled 3 h in GRT hold repair at -196 ps, 1,780 endpoints.
   The m7 kit installs `OT_GRT_NONPORT ... reg-to-output/internal retained`, so the same stall waits behind the route
   on every new kit. Not reached here.
6. **DRT-0255 (FABLE-PD-DRT-1350) is not yet measurable on hg / hgi:** no kit of the family has reached detail route.
   INFERENCE: the landing-ring nets at the e2 south edge (1c row 2) are the net class that fails there.

## 3. Fixes, ranked

| # | fix | evidence | owner |
|---|---|---|---|
| 1 | Close the m7hg_g row as done: obsolete merged netlist, route answer delivered (1c). No fix lane, no relaunch. The kit can be deleted after this report | 0.3, 1c | TYPES-KV-FAIL-1115 |
| 2 | Post 7u READY+ADOPT and switch the wave (plan, R8 table, bind dir, source tree at or after main with `replica_keep` r140). Until then nothing on hg / hgi can change | 1d | KV-102, then KIT-OPS-5 |
| 3 | Two pilots first, not 21 rows: kv3_hgi_v2__cl2862d491 and one hg frame. Read at CTS: `ti_b` banks 6 of 6, setup against -329 ps (t_hgi2) / -739 ps (k_hg), `ot_relay_mid_stations.txt` not empty. Route only if CTS setup is within reach of -42 ps | 1d; KVOVF 12, 14 | TYPES-KV-FAIL-1115 |
| 4 | kv3_hg (and any hg frame over 400k cells at CTS): split in the plan before volume. Measure the cell count per hg frame on the first 7u synth and split those above the cap; the cut needs the crossing-bus count, which I did not derive | 434k / 504k cells, 15.5 h | KV-102 (plan event) |
| 5 | For KV kits with `kv3_head_eighth_*` cores: `-congestion_iterations 15` on the full route and the same bound on the incremental call (it has none visible in the log). The residue is capacity-0 cells inside cores and allow-congestion is already on | 416 -> 36 -> 53 for 2 h 47; 5 h 51 silent | GENBUG-IMPL (grt183_make.sh / gen env), KIT-OPS-5 applies |
| 6 | M7 core close: per type, by measurement. Keep it off for kv3_hg (2 -> 53 markers); on hgi_v2 only if the keep form still needs it (keep alone gave 3 markers, REPORTED KVOVF 11.1) | 1c | TYPES-KV-FAIL-1115 |
| 7 | One count-only test on the pilot's 4_cts.odb: long wires and buffers at `-max_wire_length` 120 / 143 / 200, then set `OT_MAXWIRE_UM` for the family from that | 47,312 wires, 61,470 buffers, 2 h 16 | TYPES-KV-FAIL-1115 |
| 8 | Decide the output-port hold form before the pilots enter GRT: either the `hold_hb4` rows on output buses (TYPES-KV-FAIL READY-ROWS) or no reg-to-output repair in GRT with the check at the die. Without one of them the pilot stalls as hgi_v2 did | REPORTED -34..-40 ps per port flop; 3 h stall | KV-102 |
| 9 | Add `repair_antennas` to the allow-congestion wrapper (KVOVF F2) so wave kits do not need `SKIP_ANTENNA_REPAIR` | 1d | GENBUG-IMPL |
| 10 | Watchdog: in 5_1_grt take the metric from the current command. Before the first `repair_timing` line use log age + busy cores; do not match the legalizer `Violations` table | 0.1 | NOPROG-WATCHDOG |
| 11 | (491-508, 1305) below ectl q1 / q2: the astk `ctl_qo` landing ring and the `q1_t0` bus share full columns. Look at it on the first 7u kv3_hg placement; no row proposed from this data | 4 markers, 3 HOT marks | KV-102 |

## 4. Stop list

1. No relaunch or "structural fix" of m7hg_g, m7a, or any hg / hgi form built from a kvgeom5 / kvgeom6 kit.
2. No hg / hgi launch on kvgeom6, in the wave or privately. No lift of the 21 holds before the plan switch.
3. No reading of "repair_Violations 0 / 15 rows" as hold-repair data.
4. No M7 core close as a family default. No M8 / M9 grant, outline growth, density or routability form as a congestion
   fix: usage is 13.9 % and M8 is 2.4 % used.
5. No count of the per-layer "total congestion" (232 here) as a blocker; no 30-iteration pass to chase capacity-0 cells
   inside cores.
6. No full kv3_hg route attempt above 400k cells without the split decision.
7. No volume launch of the 19 types on 7u before the two pilots report CTS.
8. Still in force: FABLE-KVOVF section 8, FABLE-PD-KV-1200 stop list, FABLE-CLOSURE "no port-hold pads" until item 8 is
   decided.

## 5. Not checked

- What the router did in the silent phase (no log lines, process gone, no stack). Section 0.2 is inference from the
  iteration cost, the busy core and the residue.
- Whether attempt 14 (the 2-marker control) had `OT_PG_TRACK_TRUTH`; so the 2 -> 53 change is M7 close and possibly
  track truth together.
- Cell counts and CTS timing of any hg / hgi type on 7j / 7u (none built). Sizes of the other 7 hg frames.
- Whether the 7u wave source tree will carry the keep automatically for `qkh_head_tstage` (`ti_b`); check on the pilot.
- Whether the y 552.6 and y 337-345 edge rows coincide with an M6 PG pair row (DRT-1350 class).
- The 7u READY+ADOPT state after 14:4x PST; the main branch state of `grt183_make.sh` beyond the intel2 checkout.
- The gain from a larger `OT_MAXWIRE_UM`; the clock taps of this kit (layout review: clock smell "not computable").
