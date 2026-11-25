# QC-COMPOSE-GUARD handoff (narrow lane from QC-ALLFIX, 11-24 15:28 PST)
Job: find every row/setting that QC C1k dropped or reverted, write the restore delta for C1l (QC-CB-C1L), land compose_drop_guard on main.

## Method (epyc7 /srv/opentallas-scratch2/claude/QC-COMPOSE-GUARD/)
- an/hist.py: chain C4 81fd3e6370c0 -> C1b 62ce8aba0292 -> C1c 3b12251bfd6c -> C1d c2856018af83 -> C1e b6211ae9de47 -> C1f 9e75f8b4a805
  -> C1g 96cce77c1e2f -> C1h 894e6f21991f -> C1i 3e46ebd69a97 -> C1j/C1k 7fbc73d3f7cf, flattened (partition_types.T.key.sub, die keys
  depth 3), DROP/REVERT per step -> an/hist_chain.json.
- compose_drop_guard.py (finer: list elements keyed by name/conn/inst/id) on each step: an/g_fg, g_gh, g_hi, g_ik .log/.json.
- an/rowchk.py: every adopted private row (ROW vs its BASE) checked against C1k -> an/rows_vs_c1k.json.
- C1h was NOT composed from C4: guard C1g -> C1h = PASS (0 drops, 0 reverts vs C1e/C1f). C1h = C1g + F16 tie + DEADIN as posted.

## DROPPED-ROW LIST (C1k vs earlier plans and adopted rows)
| # | type(s) | key path | old value / sha | carried by | in C1k | replaced on purpose? | restore |
|---|---|---|---|---|---|---|---|
| 1 | 11 st_a: sle_st_a_v1 cl67389ecd, cl989804f6__cl18eece69, cl989804f6__cled3c1d7b; sle_st_a_v2 pv30dda31f__pv88773f93, pv30dda31f__pvd2ec7769, pv4242de79; slw_st_a_v1 clb036e152, clfc5867a6__pvf82a6c28, clfc5867a6__pvdf8e5ca4; slw_st_a_v2 clf4365a62, cl9f076a5c | ft_slots, hard_cores (btab g_btb[*].u_m origins), internal_stations (x_ctl_o from_um/bit_sites), relay_sites (+5.7k..13.1k keys per type), note; clock.{added_taps, landing_contract, landing_reader_start/_writer_start, tap_chain_affinity, tap_span_um, taps}; die clock.tap_offset.per_port_ps[type] (re-keyed by site, 207 old rows removed) + tap_offset.source | r10 0104b4703368 on C1g = plan_c1g_sta10 3c17478ed804 (QC-OPEN-STA, strict 0 / LAT 1922 04:19) | ABSENT: C1h/C1i/C1j intake never took it (not a compose bug in the merge; an adoption miss). Guard C1i->C1k --row r10: 127,706 ROW-DROP/ROW-LOST paths | no | STSLW-R1 462b3c863bb6 carries 9 types; 2 types (pvd2ec7769, pv4242de79) hand-rebased here |
| 2 | sle_st_a_v1__cl989804f6__cl18eece69, slw_st_a_v1__clb036e152 | partition_types.T.landing_relay_start_copy | true on the 9 siblings | never set on these 2 in ANY plan C4..C1k (checked C4, C1b, C1g, r10, C1k) | absent | n/a: missing row, not a compose drop | STSLW-R1 sets true |
| 3 | sle_ctl__cla4f6f12f | clock.added_taps / landing_contract (75 paths) / taps, hard_cores cl_x_hc1_st_b_i + cl_cws2_i origin_um, 24 RP-SEL relay_sites r[*][518/519], clock.added_taps clk_t259.. | HC1-CLKENTRY (C1e b6211ae9de47, eea24acd048a) | REVERTED to C1d at C1f->C1g | C1d form (+ later re-key / spread rows) | YES: COORD did not adopt (QC-HC1-CLKENTRY stand-down 03:54, "row not adopted per COORD"); RP-SEL straps came back via SEAT-MATCH re-key/spread | none |
| 4 | sle_ctl__cla4f6f12f | relay_sites: 15,996 old keys (u_pd11_x_fw_i_0.q ...) | C1h | DROP at C1h->C1i | re-keyed names | YES: SEAT-MATCH-AUDIT re-key 1d3b1fa2e6df (FABLE-RC-QC 02:56 accept); rowchk: 44,462/44,462 re-key paths CARRIED | none |
| 5 | coll_core | clock.reset_tree_anchor.relays rst_rl_63/173/287/305/449 | C1i | DROP at C1i->C1k | 5 relays re-solved, new names | YES (derived): anchor re-solved, inputs.sink_bins hash changed in the C1j compose | none |
| 6 | 2 sle_st_a_v2 types above | clock.landing_contract.pins fclk_out_x_ctl_o / x_fe_o / x_fw_ctl_o source_clock_tap | C1j FWD repoint (fwd_measured_0718, exact-coordinate) on C1g numbering | conflicts with r10 renumbering | C1k names clk_t109/clk_t6/clk_t115 | kept: C1k's tap SITE re-keyed onto the r10 grid -> clk_t103 / clk_t8 / clk_t110 (13.5-15.2 um) | in restore |
All other adopted rows are CARRIED in C1k: SC3-MONLEG bae02a9c26cb, sc3_col (C1h), OPEN-SU e1254b6b9eb4, RSTCNT 9cb276998d14, SLECTL re-key 1d3b1fa2e6df, SLECTL spread b8c397460805 (4722/4722; 1 internal_stations changed later), SC-FARRST 1dfd9d3d7464, FWCPL-2 02ddf1a18df7, CBN-TAP 4a36e4c81d4b. Chain C4..C1f: 0 drops, 0 reverts at this depth.
Not a drop (new in STSLW-R1): sle_stm bus:flt_o 2 stations + sl_E?_stm__flt lanes 0 -> 2.

## RESTORE for C1l (on top of STSLW-R1)
- Plan: epyc7 + epyc11 /srv/opentallas-scratch2/claude/QC-COMPOSE-GUARD/rows/plan_c1k_stslw_r10full.json **3d81651854c4** = STSLW-R1 462b3c863bb6 + r10 on sle_st_a_v2__pv30dda31f__pvd2ec7769 and sle_st_a_v2__pv4242de79 + r10 tap_offset.source string. Changes vs C1k: 11 st_a types + clock.tap_offset (+ STSLW's sle_stm / lanes).
- Script: rows/rebase_r10_2types.py RT_TOOLS TREE_PLAN STSLW_OUT C1K C1G R10 R10_DELTA OUT (rt 1145a6e17e79 tools; asserts the 2 types are unchanged since C1k and that C1k vs C1g differs there only in landing pins; self-check: re-keying the non-repointed pins by site reproduces r10's own names).
- Drop list: rows/c1l_r10_drops.txt 7e46904ec835 (r10's intended renumber drops: 207 tap_offset rows + added_taps).
- Guard: compose_drop_guard.py C1k.json plan_c1k_stslw_r10full.json --row r10=C1g:plan_c1g_sta10 --drop-list c1l_r10_drops.txt = PASS 0 silent (232 intended).
- Not run yet on it: PRE / strict bind (C1l bind covers it). For C1l: apply this plan as the st_a+stm row (merge3 base C1k), then run the guard vs C1k with --row r10 and the drop list.

## GUARD
tools/die_plan/compose_drop_guard.py (+ test_compose_drop_guard.py); plan_gate_pre class COMPOSEDROP (WARN with --baseline-plan; OT_COMPOSE_DROP=fail, OT_COMPOSE_DROP_LIST=FILE).
Landed: main e827d53ab617 (f505601048 tool + PRE hook, e827d53ab6 test fix), ot-push-main attempt 1, touched tests passed. Announced to S81-ALLFIX-INT / KV-ALLFIX 16:09.
## Status 16:10 PST: job done. Open for QC-CB-C1L: fold 3d81651854c4 into C1l, then run the guard C1k -> C1l with --row r10 and rows/c1l_r10_drops.txt (+ its own drop list).
