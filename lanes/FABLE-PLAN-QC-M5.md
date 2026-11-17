# FABLE-PLAN-QC-M5: structural review of QC plan event S4q9m5

2026-11-17 06:47 PST. Plan `zz_s29_qc103_s4q9m5.json` sha cf3ee3ca9c40 (M4 32bba5467a18 + rows), bind s29q103S4Q9M5BR
(epyc2 unit oth-ubuntu-3449953-1794921709, R8 c66ea4c01d38, side 5787a70f3b01). Read-only. Probes through ot-run on epyc2
(units oth-ubuntu-168485, -206549, -238714); scripts and outputs in `epyc2:/srv/opentallas-scratch3/claude/fable-plan-qc-m5/`
(p1-p3.py, p1-p3.out).

## Verdict: ADOPT M5 + M5BR. No blocking finding on the plan. One condition on the adoption source (A1), with a lane check.

CB16 on M5BR (`gates/cb16_qual_s29q103S4Q9M5BR/post_receipt.json`, bind ended 06:22:47 rc 0, G0 ended 06:10):

| criterion | read | result |
|---|---|---|
| bind errors | 0 (377 partitions, 133 types, 1,921 crossings, 0 type splits) | PASS |
| extra | e2f94854: 124 replaced + 344 inner = 468 / 468; inner 345 / 345 matched, 0 stale | PASS |
| R8 pinned | rc 0, changed 0, stale 0, uncovered 0, table c66ea4c01d38 | PASS |
| column pads <= 9 | max 0, W5 S = [0, 0, 0, 0], 12 slices | PASS |
| LATCHECK | 1,921 / 1,921, 0 unobserved | PASS |
| hcparam | 22 param_wrap types, 0 no_bound_rtl, 0 mismatches | PASS |
| G0 | 0 errors, 0 latency, 463 warnings | PASS |

Open at the time of writing: the chain unit is still active in stage S5 (shadow kit-rtl, 3 types done at 06:40), no
CHAIN_DONE line yet. S5 runs with the treeJ `param_wrap.py` a5e86017 (pre-D2). A "tail1 has no port table" there is the
tool vintage (see A1), not the plan.

## (1) Does M5 change only what the measured rows justify? Yes in kind, no in extent.

My own diff M4 -> M5: 5,748 leaf keys = 4,931 tap_offset + 1 source + 816 tap_window. 0 outside `clock.*`. 0 latch_except.
Seam 160 kept (need 147.87, margin 12.13).

| set | types | offset port rows | window keys | what the M4 proof says |
|---|---|---|---|---|
| justified | 3 `sle_st_b_v1` (E0 / E2 / E4, 1 instance each) | 382, max move 32.2 ps | 308 (268 up, max +34) | 61 checks outside the M4 rows (57 + 4 on the new port `clk_t128`); 17 ports with window need above the M4 window by up to 33 ps; FF intra contract -13.26 ps on 18 pairs (W 57, need 70.26) |
| churn | 11 live types | 1,554, max move 1.1 ps, max tol move 1.1 ps | 506, -3 .. +1 ps | 0 checks outside the M4 rows; need <= M4 window on every port |
| cleanup | 2 dead types (0 instances) | 355 dropped | 355 dropped | none |

- On the M5 rows the gate is clean: 84,506 checks, 0 outside, min margin 10.0 ps.
- The 11 churn types: cbn_q00__cldbcda913 (15 rows), cbn_q01__cld9ff4c40 (2), cbx_q10__cl89936551_h (1),
  sle_ctl__cl503337ff (111), __padE0 (171), __padE4 (171), sle_ctl__cl67434795 (204), __padW5 (265),
  sle_st_a_v2__pv30dda31f__pv88773f93 / __pvd2ec7769 (242 each), slw_hc3__clccfc3e6b (80),
  slw_st_b_v2__pva66d0f22__pv3d7bec84 / __pvb80e2003 (24 / 26). The only raised windows are 6 ports of
  slw_hc3__clccfc3e6b, +1.0 ps.
- Cause: `rows_m.py` rewrites every row at need + 10 on each run; it has no hysteresis. Harmless for the bind, but it
  must not trigger kit work: these types stay 8.9 ps or more inside their M4 tolerance.
- The bind did not need the rows at all: M5BR `bus_groups.json` b2a22350a177 is identical to M4BR, and the two bind logs
  differ in 2 lines (start line, end line). M5BR spent 3,633 s to reproduce M4BR.

## (2) Stale data

- M5 rows: fresh. Proof `s4q9m4/reg/proof` 04:59, kitoffs / kitwin 05:12, all stamped plan 32bba5467a18 and checked by sha.
- The stale rows were in M4: its rows came from the `s4q9m_l2d` proof (plan a915f1136c27, three plan steps back). That
  is why the gate failed on M4.
- M5BR carries 6 files older than its launch (`asbuilt.json`, `asbuilt_sources.json`, `asbuilt.ys`, `asbuilt.yosys.log`,
  `asbuilt_lib_stubs.sv`, `provenance_elab.json`, mtime 11-16 10:38-10:39). They are hard links of the L2BQ seed
  elaboration: `asbuilt.json` ec5fb2617e74 and `asbuilt_sources.json` ed45aca575c3 equal in L2BQ, M4BR and M5BR. By
  design. The elaboration names only the base `qfd_dv_s8_station_tail1` (and `_nb0`); the five M4 masters exist only as
  param_wrap rows, and hcparam (22 types, 0 mismatches) is the one check that ties them to the bound RTL.
- No superseded M3 / M4 view is read. The die STA reads no view at all (see 3).
- Label only: the bind log header prints `r8=f6d2f5e120f4` (the old KF table). The table actually bound is
  c66ea4c01d38 (INPUTS_ISOLATED, receipt, R8 check changed 0).

## (3) Clock / CA credit

- The 833.333 readout cancels exactly. `mk_combo_kv.py` line 27: late arrival = 833.333 - slack_max_rise on a virtual
  clock of period 833.333, input and output delay 0; early arrival = slack_min_rise. The period drops out. Even if it
  did not, the exposure is 0.333 ps against a CA worst margin of 105.0 ps (5.0 ps above the 100 ps flag line). The die
  STA and CA run at 833.0. No re-extract.
- CA_C / CA_D: 2,993 crossings, 0 fail, worst lo 105.0 / hi 112.5, 724 / 724 start edges clean, 300 MC chips 0
  violations. This is TT nominal with CPPR, no OCV term; the SS scaling (483 fail) is INFO. CA does not read the rows.
- What the STA is: `block_model` = declared-budget, kits_found 0, core_views_found 0, core latency 250 ps declared on
  both sides, 1,461 early core taps declared, 0 of 7,982,308 hold pairs measured. The five signed M4 masters are in
  the missing-view list. So TT intra +403.6 and seam +550.1 are tree-on-model numbers, and BLOCKED(kits) is the right
  verdict. The lane claimed no die clock PASS; that is honest. Do not quote +403.6 as die setup.
- Inherited, not M5: 820 taps above the 320 ps slew limit at TT (486 at FF), max 434.0 ps (sl_E3_hc1 `clk_t13`), all on
  hc1 / hc2 types. Same count and same maximum in the l2d proof. For the clock lane in N, not for M5.

## (4) D2 / D3 against M5

Production is L2 (plan 19be3f0a, rows from the s4q9c proof). Two interactions, both with numbers.

A1. Tool lineage. The M5 bind tree (treeJ) and the D3 source differ in three files that decide kit GEN:

| file | treeJ (M5 bind) | D3 f6917f02 |
|---|---|---|
| `tools/die_plan/bind.py` | 049b2db8c640 | 049b2db8c640 (same: the bind is reproducible) |
| `hard_landing.py` | 8ce0460c8ed0 (old prove, 0 x LOCAL_PASS_NEEDS_PARENT) | 21b1ba392182 |
| `param_wrap.py` | a5e86017976a (pre faf8c5cd61f) | 24227e8ffa5b |
| `gen_phys.py` | a4d936a65078 | d9a8e1459a41 (the pre-D2 pin has a third one, 9b087b556d88) |

An M5 source cut from treeJ brings back both failures that D2 / D3 just removed: the tail1 "no port table" class on
the st_a param_wrap types (22 param_wrap types in M5) and "hard landing requires SIGNED child" on the 8 sle_ctl
landing children. `gen_phys.py` is the file that turns the rows into kit SDC, and the rows were validated with a
fourth copy (fable-die-qc-r/src5).
Lane check (QC-PLAN-R3, minutes): from the D3 tree, on the M5 plan, run `gen_phys.tap_offset_table` and
`tap_window_port_table` on all 133 types (0 errors, `clk_t128` present on the 2 st_b types) and kit-rtl on the 22
param_wrap types (rc 0). If either fails, do not publish M5 until it passes. If both pass, publish M5 = D3 tools + M5 plan.

A2. The 8 rows D3 released at 06:30 build on L2 and do not survive M5:

| type | M5 vs L2 |
|---|---|
| sle_st_a_v1__cl989804f6__cl18eece69 | 4 stations h16_n9_s10 -> h17_n7_s8; 170 ports outside the L2 tolerance |
| sle_st_a_v1__cl989804f6__cled3c1d7b | 4 stations h15_n9_s10 -> h17_n7_s8; 210 ports outside |
| sle_st_a_v1__cl67389ecd, slw_st_a_v1__clb036e152, slw_st_a_v1__clfc5867a6__pvf82a6c28 | same type row; 176 / 159 / 144 ports outside, up to 57.3 ps; windows up to +89 ps |
| sle_ctl__cl372cea1c, __cl503337ff, __cla4f6f12f | landing child gets its lef / lib; 40 / 25 / 217 ports outside; cl503337ff goes 5 -> 4 instances |

Die-wide, M5 rows against the L2 rows: 112 of 133 types have at least one port outside the L2 tolerance (6,034
ports), 114 types have a raised window (9,237 ports, up to +94 ps), 7 types are new. So an L2 build is a fail-round
test of the D3 fixes only; its result is not an M5 result. The STA re-sign set at adoption is about 112 types, not 3.

## (5) What could make M5 the sixth event without convergence

Rows move with the tree, not with the plan. The M4 chain copied 198 of 240 regions from its template and embedded 42.
On 11 types the rows moved 1.1 ps or less; on the 3 st_b types they moved 32 ps (I infer these sit in re-cut regions;
I did not map them). Between
the L2 tree and the M tree they moved up to 57 ps on 112 types. Every later event that rebuilds the clock tree
(N START with 4 new flops and N + 2 / K + 2, SC reset, the bit-level latch_except, R-REACH-4) re-cuts regions, moves rows
past tolerance + 10, and forces another rows fold, another tag, another 60-minute bind and another die-wide re-sign.
The rows are also still cut on a model die (0 kits, 0 views): real views will move them once more.

The single change: make the clock a record of its own. Freeze the M4 tree (`s4q9m4/kit/clock/tree.json`, 04:27)
together with `rows.json` as the clock of record, keyed by tree sha, outside the plan tag; later events take that tree
as template and re-cut only regions whose tap set changed; a row is rewritten only when the tap-offset gate or the
window need fails on it. With that rule M5 would have been M4BR (final at 05:05) plus a 3-type row delta, with no
second bind.

## Stop list

1. A rows re-fold or a clock chain re-run on M5 "for the plan sha". The M4 proof is the M5 proof.
2. A new tag or bind for a rows-only delta (M5BR = M4BR, bus_groups b2a22350a177).
3. Kit relaunch or re-sign of the 11 churn types on a row change of 1.1 ps or less.
4. An M5 source cut from treeJ or from the pre-D2 pin.
5. More L2 launches of types M5 re-masters or re-rows once M5 is published; L2 fail rounds counted against M5 types.
6. Separate events for latch_except (bit-level), N START, SC reset and R-REACH-4: one event N, on the frozen tree.
7. Port-level `latch_except` in any plan (FABLE-PD-QC-0600; M5 has 0).
8. A die clock or hold PASS, or "+403.6 die setup", quoted from this STA.
9. Slew repair of the 820 hc1 / hc2 taps inside M5.

## Not checked

Sign-off state of the 133 types (so the re-sign count is types, not builds), the S5 / S6 stages of the CB16 record
(still running), whether kit identity hashes the rows, routed timing of any M5 type, the D3 `gen_phys` check itself
(A1 names it), CA under OCV.
