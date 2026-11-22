# FABLE-FIX-HEAD-LEP0N-R5 (Fable, 11-21 19:25-19:5x PST): hd_lep0N type split, steps 1-2 tools + cut census (successor of R4)

Predecessor: lanes/handoff/FABLE-FIX-HEAD-LEP0N-R4.md (rename map, RTL facts; still valid) + lanes/FABLE-PD-HEAD-2000.md.
Lane dir intel2 L=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-r5 (clone = lane clone of main, plan/, tmp/).
Stood down on context, not on a blocker. No kit launched. No plan event, no live tree written, nothing resealed.

## In flight (1 unit, adopt it)
- oth-ubuntu-1136304-1795317736 (epyc9, R4's six-content 0-cycle equivalence). Hub log intel2
  ~/fable-fix-head-lep0n-r4/parts_equiv_e9.otrun.log, proof log epyc9
  /srv/opentallas-scratch2/claude/fable-fix-head-lep0n-r4/parts/proof/parts_equiv.log.
  State 19:36 PST: equiv_simple proved 349,132 of 351,685; the other 2,553 are in "6. EQUIV_INDUCT" (normal: Codex's runs
  also finished in induction). NOT proven yet. Pass = "Equivalence successfully proven" then PARTS_EQUIV_PASS.
  Do not quote the six-content form as LEC-clean before that line. If cells stay unproven: R4 handoff, "In flight".

## Landed on main (ot-push-main, tests run)
1. 01fa4a7bcd9 type_split.py + landing_place.py (work order 1, done):
   - type keys `nets`, `sources` handled. A net inside one piece stays; a two-leaf net across pieces becomes a cut route
     (bus pair o_<net> / i_<net> + port + lane; both content binds re-pointed). Spec `net_drivers {type: {net: "inst.port"}}`
     is required for every cut net, `net_kinds` optional. Fails closed: undeclared / leafless net, 3-leaf cut net, no driver.
   - spec `content_params {type: {inst: {param: value|null}}}`: parameter delta applied WITH the split (boundary pair in
     place of native stages); spec `native_stage_drop {type: [regex]}`: stage rows that no longer exist.
   - landing_contract.native_stage_groups per piece: rows follow their content, rect shifted, must lie in the piece.
     New v2 form {schema ...v2, contents [{content, module, params}], groups}; landing_place accepts v1 and v2.
   - 13 new tests in test_type_split.py, 8 in test_native_stage_groups.py. Unit level only: no gen-mode type has run
     through Event.run() end to end yet (see blockers).
2. tools/s81_head/head_lep_parts_delta.py + test (push in flight at stand-down: check `git log origin/main -3 -- tools/s81_head`;
   log L/tmp/push2.log; if absent, the commit is on branch claude/fable-fix-head-lep0n-r5 in L/clone, run ot-push-main there).
   One-content plan -> six contents + 17 two-leaf nets + every carried path renamed. Run on v2 plan 00b2abf6e7a6:
   L/plan/plan_parts.json, report L/plan/parts_delta_report.json. Counts equal R4's census: hard cores 24 moved / 25 hub,
   stage groups hub 136, io 18, rg0/3 14 each, rg1/2 22 each, bus leaves 12, core taps 4, internal stations 3.
   landing_place validates the v2 groups (226). NOT done on it: gen.py rtl elaboration, cohort, strict bind, LATCHECK
   (needs the parts RTL in a private tree: epyc9 R4 parts/proof/ot_s81hd_lep0N_parts.sv + base/split_tx_io_stages.sv;
   neither is on main).

## Cut census (draft spec L/plan/split_spec_we.json; read before writing the real spec)
Measured on plan_parts.json against cuts 907.2 / 1745.28 (script output, 19:5x PST):
1. The E strip cut (1745.28) does not fit the contents: 11 of 18 u_io stage rows sit west of it (pin_r2/r4/s2/s3/s5u,
   pout_r0/r2/r4/s0/s1; pout_s2 straddles), and plw_s2 (hub) sits east of it. The io stage chain IS the reach path from
   the E face to the hub. Use ONE cut at 907.2 (W | E), io in the E piece, unless io is first split by stage index.
   Cell count allows it (R4: E about 300k, W about 100k).
2. Hub (E piece) items that sit in the W piece today and must get E sites before the split (site moves, shapes fixed):
   8 RX SRAMs (g_rx[1], g_rx[2] banks; e.g. g_rx[1] bank 0 at x 794.99), 5 u_land SRAMs (2 in W, 3 straddle the cut,
   x 613.5 on), stage rows krx1/krx2 hub side (r4, s1: 8 rows), txread_l 10, rxbank_l 9 (6 straddle), wdq_bank 2,
   c0i_s0 and plw_s1 straddle. The 10 TX SRAMs of lanes 1, 2 leave the E band for the W piece, which frees their sites.
3. W contents with rows east of the cut: txi1_r0, txi2_r0 (E), txi1_s0, txi2_s0 (straddle).
4. N-face buses: coll_i0 window 609.28-815.28 is wholly in the W piece and coll_o0 831.28-1036.48 straddles the cut, but
   both leaves are the hub (E). Either move both windows east of 907.2 (die-side port move), or use spec clip_windows for
   coll_o0 and let coll_i0 cross as an internal-station leg with COL0 2 -> 0 so the boundary pair costs no cycle.
5. type_split still fails closed on hd_lep0N at: type keys id_straps, private_reset_start_exports, reset_start_raw_exports;
   clock keys insertion_basis, insertion_ff_ps, landing_export_form, landing_reader_start, landing_status_anchors,
   landing_status_input_stages, landing_writer_start, reserved_sites_um, reset_tree_anchor, start_capture_um, tap_group,
   tap_grt_pre, tap_model, tap_passthrough. Scalars can be copied; the START / status / reset-tree keys are derived by the
   HEAD prep (NF15f) and must be re-derived per piece (spec drop_clock_keys + rerun prep), not copied.
6. KRX leg renames: with KR 6 -> 4 and RA 3 -> 2 on lanes 1, 2 the surviving stage instances change index (hub g_rxf
   starts at g_s[RA]; region g_rxr starts at g_s[KR-RA]), so the stage rows need a rename, not only native_stage_drop.
   The cut form (boundary pairs in place of 2 native stages) also needs its own equivalence proof; R4's proof covers
   only the uncut RXA 16'h0330 form.

## Work order left
1. PARTS_EQUIV_PASS. Then a private tree (real copies, nlink 1) of v2 + parts RTL + plan_parts.json: gen.py rtl, cohort,
   strict bind 26/26, LATCHECK 329/329 with NO cut.
2. Plan rows before the split: census items 2-4 as site moves + the three PD rows (RX row y 637.7 break, coll_i1 / coll_i2
   re-seat, measured OT_PREGRT_HOLD_R2R_MARGIN as --ab).
3. type_split: census item 5 (per-piece HEAD keys), stage-row rename for item 6, W local reset fan for rs1 / rs2.
4. Spec with one cut 907.2, split, strict bind + LATCHECK + G0; kit_wave.py private-spec for both pieces (epyc9 / epyc7,
   wave env, config.mk diff); routed LEC.
5. Reseal r17a v2 with split rows + HEAD-CTL-R1 WRCAP row on a private live copy; reconcile live_s81_head 81ac28d4 first.

## Infra
- intel2 python is 3.14; tools/die_plan tests need physical/common_flow in the sparse cone.
- epyc9 scratch2 650 GB free at 19:25 PST.
