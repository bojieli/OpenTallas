# RULEBOOK 11-13: family design rules set by Fable expert lanes

The owner (11-13 03:4x) asked Fable expert lanes to set the few family-level physical design rules that keep recurring, once, up front. COORD and every lane follow these rules. Each rule has an ID, the rule, why, the implementation (tool and sha), its proof kits, and the dies and types it touches. Only the owning Fable lane edits its own section.

Expert review evidence: ~/coord/lanes/EXPERT-REVIEW-1.md

## R-CLOCK (HOLD-TAP-1): cross-tap insertion balance for zero-logic and low-logic pairs
## R-RTL (HARD-S81-SERDES-1): pipelining depth for paths over budget
Written 2026-11-13 03:29 PST by HARD-S81-SERDES-1. Status: rule text final; the S81 serdes proof build is still running (see lanes/handoff/HARD-S81-SERDES-1.md). Numbers are read from existing reports (TIMING-CLASS-1 census 11-12, serdes__t2 attempt_27 4_cts_final.rpt, CORES-HBM-1 rx_bm3 probe); I ran no new STA sweep over the dies.

**R-RTL-1 stage budget (833 ps, TT).** 833 - 60 uncertainty - clk->Q 60..90 - setup ~25 leaves about 650 ps; keep 50 for skew, so 600 ps for cells plus wire. Measured cost: 29..34 ps per logic cell at light load (hidx 757 ps / 22, svc_vm 794 / 27, serdes am_ok 203 / 6), about 60 ps per cell when a cell drives 80+ loads (hd_host_w 617 / 10), about 0.8 ps per um of repeated wire (serdes u_txl 1267..1674 ps over 1.7..2.2 mm). A stage must fit
`32 ps x logic cells + 0.8 ps x um (pin to pin, Manhattan) + fanout terms <= 600 ps`. As a table:

| launch-to-capture distance | max logic cells (buffers not counted) |
|---|---|
| <= 100 um | 16 |
| <= 250 um | 10 |
| 250..405 um | 3 (mux / enable only: this is a relay hop) |
| > 405 um | 0, and one register row per 405 um (12.1e) |

**R-RTL-2 fanout inside a stage.** A net with more than 64 loads is not one cell: give each group of <= 64 loads its own registered copy of the source (enable, select, reset, valid). The copy is placed with its loads. Never close a wide broadcast with buffers.

**R-RTL-3 macro ports.** After a memory or hard-core output (clk->Q measured 365 ps on the serdes dmem): at most 5 cells and 100 um before the next register; if not, register at the port and read one address earlier (0 cycles) or take +1 cycle. Before a macro input (setup 131..194 ps measured): at most 8 cells and 100 um.

**R-RTL-4 where the check runs.** (a) At synthesis, before any place and route: count non-buffer cells per endpoint on the 1_synth netlist (STA with zero wire). Any endpoint over 16 cells or 520 ps of cell delay is an RTL item; the kit does not go to placement. (b) At placement, split every failing path into logic / repeater / wire. Repeater + wire > logic means the path is a reach or placement item (R-REACH, lane rows), not a depth item; adding logic stages will not fix it and rebuilding will not either.

**R-RTL-5 the fix, in this order.** (1) Restructure the cone: parallel-prefix instead of ripple, balanced tree instead of chain, registered partial products for wide XOR matrices. 0 cycles. (2) Retime an existing register into the cone. 0 cycles. (3) Add a register stage, +1 cycle (owner pre-approved). No settings, retries, ECOs or relaxed constraints in place of these.

**R-RTL-6 latency bookkeeping for every added stage.**
- The stage is a parameter or define, default off; default off must be flop-for-flop the old netlist.
- Data, valid and the reset that defines the frame or calendar move by the same edges. A stage that moves data but not its reset is a bug even when a loopback still passes.
- One lock-step bench per form: new(t + N) == old(t) on every edge outside reset, through cold reset, warm reset and any local reset sequencer. The bench also carries at least one mutant (a row short, or a reset not moved) and one wrong expected N; both must FAIL.
- One row per added cycle in results/<lane>/latency_rows.json: id, lane, parameter, added_cycles, clock, relative_to. The row goes to the die owner and TOK-VERIFY with the READY.
- The plan type carries the parameter (verilog_defines); after the bind, tools/die_plan/lane_asbuilt_latency.py must PASS on the bound plan. Internal stages of a link (serdes, PHY) that the lane table does not count are still reported as rows.
- Registers added for reach are placed by rule (FIRM at their per-bit lane site before global placement), never left to wirelength-driven placement: it puts all rows of a 2-pin chain at one end.

**Types over the rule today** (source in brackets; "unmeasured" means no path report exists, not that the type passes):
- HBM ot_hidx_s3_q: 22 cells 757 ps, TT -203.5, 160 endpoints. R-RTL-1. Fix: prefix adder for the s3 sum, else +1 stage. [TIMING-CLASS-1]
- HBM ot_hbm_svc_vm_kshare_splitstrap__v700685: 27 cells 794 ps, TT -36.2. R-RTL-1. Fix: balanced priority tree or retime sm_s. [TIMING-CLASS-1]
- HBM ot_hbm_svc_vm_kshare_splitstrap__v8e478a: fanout-64 c_k_rdy broadcast, 475 ps of buffers, TT -68.0. R-RTL-2. [TIMING-CLASS-1]
- HBM hnx_fused_lane_c: e_rd -> SRAM wd_in, 134..291 ps single cell + 137..219 ps pin net + SRAM setup, TT -251.9. R-RTL-3. [TIMING-CLASS-1]
- HBM ot_pdie_serdes_rx_bm3_rest (5 instances): 296 endpoints sc_q -> sp (8 XNOR levels behind 100 + 135 ps fanout buffers), 90 in the rate matcher, TT -171.7. R-RTL-1 and R-RTL-2. Fix forms exist (SPCYC, OT_S81_RM_STAGED), in build by CORES-HBM-1. [CORES-HBM-1 11-12 03:47]
- HEAD hd_host_w: 10 cells 617 ps with fanout-84 and fanout-86 enables, TT -76.2. R-RTL-2. [TIMING-CLASS-1]
- HEAD hd_serdes: FAIL 11-12; same KP4 encoder / syndrome RTL as S81, cones unmeasured by me.
- S81 serdes family, 11 types (serdes__t1 x2 cohorts, t2, t3, t4, t12, t13, t14, t15 x2 cohorts, t16; one shared column RTL): R-RTL-1 row 4. serdes__t2 a27: u_txl r[0] -> q 0 logic cells, 1267..1674 ps of repeaters; PMA face -> u_syn 5..6 cells 203 ps, 1570 ps of repeaters; u_rm r_d -> coll_o register and coll_i register -> u_enc are the same class. This is reach, not depth: the fix is lane rows (this lane). The KP4 cones (dsyn sc_q -> sp, enc ch_q -> pp) are the same RTL that fails on HBM rx_bm3; I measure them on the proof build and add them here if they exceed 16.
- S81 seqhost__t1: reg-to-reg up to 1514 um, 3861 pairs over 405 um; no path report kept. R-RTL-1 row 4, unmeasured. [TIMING-CLASS-1 geom row]
- KV kv3_hub_Ei: 1 cell + 6 repeaters 745 ps, TT -159.5. Reach (R-REACH), not depth. Listed so it is not sent to RTL. [TIMING-CLASS-1]
- QC: the census has no QC setup rows; unmeasured against R-RTL-4a.
- HBM q_spb1, vsN1, vsN2 and the 10 S81 slice_station rows are clock-tap or hold items (R-CLOCK), not R-RTL.
## R-STREET (RULES-STREET-1): macro and pin-face streets, congestion escape
## R-REACH (RULES-REACH-1): fanout and reach locality, face-net buffering
## R-CAP (RULES-CAP-1): partition size, cell cap, outline sizing
Written 2026-11-13 03:57 PST by RULES-CAP-1. Status: rule final; code on branch `claude/rules-cap-1`@daf4c190d3 (parent main fbfb4fc6a6), READY posted to COORD-REVIEW-QUEUE, not yet merged. Evidence: 376 kit runs harvested from the fleet logs (S81 132, QC 76, HBM 57, HEAD 34, KV 33, 44 core kits; 10-28..11-13; epyc2/4/7/8/9, intel1/2), 295 distinct type forms kept as `tools/die_plan/testdata/cap_runs_1113.json`. Outcome labels come from `autopilot/kit_wave_stages.tsv` and `structural.tsv`. I ran no new build. Runs on epyc5/6 and pruned run dirs are not in the sample.

**What the cap measures.** Not memory, and not global placement.
- Memory follows outline area: peak RSS was at most 43 GB for every run up to 4 mm2; HBM q_mcb_ne (10.2 mm2, 765k tap cells, 189k logic) died in GRT at 110 GB. Fit over 100 runs: GB = 4.4 + 3.4 per mm2 + 0.034 per 1,000 instances.
- Global placement took at most 3.4 h, even at 1.4 M instances.
- The wall is the serial timing repair after placement, and it scales with MOVABLE cells (all standard cells except TAPCELL/ENDCAP/FILLER/DECAP; macros apart):

| movable cells after place resize | runs | finished CTS | finished GRT | routed | signed off | hours when it got there |
|---|---|---|---|---|---|---|
| under 100k | 123 | 85 | 59 | 52 | 23 | GRT 0.4, route 0.8 (medians) |
| 100-200k | 85 | 41 | 14 | 12 | 5 | GRT 3.0, route 1.8 |
| 200-300k | 74 | 41 | 3 | 2 | 0 | GRT 3.7, route 5.1 |
| 300-400k | 36 | 13 | 5 | 4 | 0 | GRT 4.5, route 3.0; all four routed at setup -146..-281 ps |
| 400-500k | 33 | 10 | 0 | 0 | 0 | one GRT ran 40 h without finishing |
| over 500k | 25 | 13 | 0 | 0 | 0 | CTS 3-5 h; 16 of 17 KV kv3_pv runs then failed FF hold at -306..-731 ps |

  "Finished" counts are lower bounds: many runs were cancelled or held for a visual verdict, so a low count below 300k is mostly churn, not a limit. Above 400k the count is zero in 58 runs, and that is the limit. The largest sign-off in the sample is 134k movable; the 10-23 record (517k standard cells, 8.8 h route) counted taps too.

**Why counts inflate after synthesis.**
- Tap and endcap cells: ORFS asap7 puts a tap every 50 um in each 0.27 um row (distance 25, staggered) plus 2 endcaps per row = 74k fixed cells per mm2 of free core. Model/measured = 0.994 median on 90 macro-free types. A partition tile runs at 1-4 % standard-cell utilization (median 2.8 %), so taps outnumber logic in most types: S81 leaf 88k taps for 20-170k logic, HBM SU 150-170k. They are fixed, so they cost memory only.
- Place buffering: median x1.41 of the synthesized count for types over 100k (p90 x2.11). One buffer per signal pin (measured 1.00), then repeaters on long nets. The repeater count follows pins x outline size and macro count x outline size, not logic: `place = synth + pins + 0.395 x pins x hp/100 + 58.8 x macros x hp/100`, hp = (W + H)/2 in um. CTS then adds 2.1 %, GRT repair 5.8 % (medians; hold repair can add far more).

**R-CAP-1 budget, per type, on movable cells.**

| stage | budget | enforced by |
|---|---|---|
| synth (pre-floorplan) | 280k, design target | none; the projection below is the gate |
| place (after 3_4 resize) | 400k, HARD | G0C `cell_budget`, kit preflight, pre-floorplan projection, place census |
| CTS | 420k | census line (advisory) |
| GRT after repair | 460k | census line (advisory) |
| any NEW type or split part | 250k after resize | G0C / preflight verdict TARGET, and the split text |

Tap, endcap and filler cells never count. The kit-level raise to 517k (`--native-cell-cap`, COORD 11-04) is for capacity probes only; a sign-off kit does not use it.

**R-CAP-2 outline and utilization.**
- A hard core (its own outline) is sized to 0.30-0.50 standard-cell utilization of its free area after resize, never above 0.55. Signed cores in the sample sit at 0.24-0.50; the one at 0.62 (467k) failed.
- A partition tile keeps the outline the die plan gives it (core-shape freeze). Its utilization is not a target. What it must satisfy is R-CAP-1 on the projection, which already charges the outline: each 100 um of half perimeter costs 0.4 buffers per pin and 59 per macro.
- Memory request per run: `ot-run --mem` = 1.5 x the fit above, at least 32 GB (`cap_estimate.py` prints it). An outline over 6.5 mm2 gets a warning: 6.1 mm2 passed GRT at 42 GB, 10.2 mm2 did not at 110 GB.
- Tap pitch stays at the ORFS asap7 default. Changing it would cut fixed cells only, which are not the limit.

**R-CAP-3 when and how to split.** A type whose projected or measured movable count after resize is over 400k is split before it is built again. No density, effort or retry setting replaces the split.
1. Parts: the smallest n with count x 1.03 / n <= 250k (the 3 % is boundary registers).
2. Where: at lane-group boundaries. Each cut bus is registered at the boundary: one station on the cut links, +1 cycle on those lanes (pre-approved), recorded as latency rows under R-RTL-6.
3. Logic with no lane groups (control, glue, a single engine) is hardened into cores of at most 250k cells at R-CAP-2 utilization, so only glue stays movable in the parent. Core shapes are then frozen.
4. A whole family is split in ONE plan event, with the same cut on every member.
5. A type between 320k and 400k projected (NEAR, inside the +-25 % error band) may launch; the place census stops it if it measures over 400k.

**Implementation** (branch `claude/rules-cap-1`, files under `tools/die_plan/`):
- `cap_estimate.py`: budgets, tap model, projection, split text. `--kit KIT`, `--plan die_plan.json`, `--validate RUNS.json`.
- `check.py`: G0C check `cell_budget` per type (ERROR with `--completeness`, WARN in plain G0). A cored type whose only estimate is a flat table (KV kv3_pv: 7.0 M flat, 0.28-0.44 M really placed) is left to the kit checks.
- `kit_preflight.py`: check `cell_budget` fails an OVER kit before any allocation. The synth count is an earlier attempt's `native_cell_count.json`, a staged `cap_budget.json`, or the plan estimate with `--plan-dir`. With none, the next check judges.
- `native_cell_cap.tcl`: the same projection on the synthesized top, before floorplan repair starts; over 400k stops the run with the split and writes `cap_projection.json`.
- `cell_census.tcl`: the place census (in `pre_cts.tcl`) stops a run measured over 400k before CTS. `OT_CELL_BUDGET_GATE=0` for capacity probes.
- Kits already generated keep their own copies; the checks act on kits generated from main after the merge. No running job is touched (freeze to 11-15 04:00 respected).

**Proof** (`test_cap_estimate.py`, `cap_estimate.py --validate`): predicted against measured post-resize movable count on the 295 distinct runs.
- 222 runs of 100k cells or more: median error 9.9 %, p90 30 %. Hold-out half: 10.1 % / 27.9 %.
- 53 runs measured over 400k: 46 predicted OVER, 7 NEAR (launch with the census stop armed), 0 missed.
- 8 predicted OVER measured under 400k: six at 364-387k (QC st_b, hc1; routed, none signed), plus S81 serdes__t3 and HBM q_spu0.
- Known limit: the model cannot see a placement blow-up. S81 dsdv_slice_*_C forms t1/t6 measured 0.87-1.43 M from 320-390k synthesized, because the second place repair pass inserted 230-740k buffers (R-REACH / R-FLOW). They are still caught, since the projection is already over 400k, but the measured count there is not a guide to the number of parts.

**Types over the rule** (measured after 3_4 resize unless marked; HBM is parked and listed last for the resume):
- S81, split needed: dsdv_slice_*_C family, 16 plan types (c1x t1,t3-t10, c3x t1, iq, kv512, lepe_mu, lepe_nh_mus, lepw_mu, lepw_mus). Synthesized 321-387k with 41-47 macros, projected 440-500k, measured 468k (t10) to 1.43 M (iq t1). Split 2 ways (iq 3 ways) at the lane groups, one event for the family. c3x t1 and five others have no run; they are the same class.
- S81, NEAR (may launch, census armed): ot_s81sl_kv_leaf t1-t5 (measured 287-360k), serdes t4/t13/t15/t16 (324-377k; their failures are R-RTL reach, not count), ot_s81sl_leaf__t47 (326k from 153k synthesized: reach).
- S81, stale estimates: `cells_est.json` gives gunit__t1 484k and eng__t1 429k; eng__t1 measured 105k synthesized, 140k placed. Refresh the table; no split.
- HEAD: none measured over (largest hd_ctl 166k). hd_lep0N has no run and a plan estimate of 365k (projected 444k): the pre-floorplan projection decides at its first build. hd_tile's 1.07 M plan figure is a flat count; it measured 68k synthesized.
- QC, split needed: sle_ctl (measured 419-451k, 20,362 pins) 2 ways; sle/slw_st_a_v1 and _v2, 4 types (421-441k, synthesized 381-397k) 2 ways.
- QC, NEAR: sle/slw_st_b_v1/_v2 (354-380k), sle/slw_hc0-hc2 (353-387k). Inside the budget; the four that routed took 9-10 h and missed setup by 146-281 ps, which is R-RTL / R-CLOCK work. If st_a is cut, cut st_b the same way in the same event.
- KV, split needed: kv3_pv family, 10 plan types (pv, v1-v8, v12; 20 cores each). Measured 423-724k movable from 281-445k synthesized soft logic; 16 of 17 runs failed FF hold after 3-5 h of CTS. pv and v8 2 ways, the rest 3 ways, or harden the soft logic between the 20 cores into cores. kv3_hub_Wo / kv3_hub_Eo (464k / 407k) 2 ways.
- HBM (parked): q_su00 757k, q_su00 pv1 627k, q_su20 pv1 633k, q_su11/pv1 446-468k, q_su31/pv1 393-428k, q_su20 413k, q_su30 396-440k, q_b002/pv1 445-778k, q_b012 762k, q_spu0 407k. The approved pEv12 split (su00 3 ways, others 2) matches R-CAP-3.
## R-FLOW (RULES-FLOW-1): ORFS flow settings for slew, DRV and early buffering
