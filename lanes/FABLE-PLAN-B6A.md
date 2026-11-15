# FABLE-PLAN-B6A: review of S81 plan event B6a (stage 1 of B6), 2026-11-14 20:3x PST

Reviewer: Fable, read only. Event: DIE-S81-92, epyc7 `/srv/opentallas-scratch2/claude/s81-b3-clk`, plan `ev/B6a.json`
(e92fef5dbb20), run `run/b/B6a`, chain `chainB6a_92.sh`, patch script `b6.py`, overlay `ovl_b6`.
State at review end (20:30 PST): G0 still running, elab and bind not started. Check 5 (bound RTL) is therefore OPEN.

## Verdict

- The bind may run on: nothing found stops it.
- F1 BLOCKS adoption of the four outline rows as written (numbers and lane check below). Fix in B6b.
- F2, F3, F4, F6 are advisory. F5 is open until the bind writes its output.

## What the plan really changes (measured: full JSON diff B3z2sc2 -> B6a, 87 leaf differences)

| Change | Count | As described |
|---|---|---|
| `partition_types/*/outline_um[1]` 1226.88 -> 1278.72 | 4 | yes |
| `die/io/*/bump_exclude_um` y 25924.8/26421.12 -> 25380.48/25876.8 | 2 windows | yes |
| serdes `verilog_defines` + TXPIPE, RXPIPE; `clock.tap_max_sinks` 100000 | 11 types | yes |
| `lanes/*/fixed_cycles` added = 1 | 14 TX lanes | yes |
| `latency/lanes/*` cycles, fixed, natural each +1 | 14 rows | yes |
| `note` | 1 | yes |

Nothing else differs. No other type block is touched.

## F1. Outline restore hides the 22 abutment errors; it does not fix them (BLOCKS adoption of these 4 rows)

Measured:
- The 22 abutment errors are four seams, all on the north face of the four types: s_0N_x03 (t41) / s_0N_x04,
  s_0S_x07 (t6 cl54a9ceeb) / s_0S_x08, s_7N_x10 (t29 clc7772371) / s_7N_x11, s_7S_x19 (t29 cl2e5c855a) / s_7S_x110.
  One instance per type. Gap 51.84 um each (e.g. 20917.44 vs 20969.28).
- With 1278.72 the slot pitch is exact for all four (origin + 1278.72 = neighbour origin), so no overlap: the restore
  is safe for the neighbours in plan geometry and G0 abutment should go quiet.
- All four types are SIGNED, and each signed DEF has `DIEAREA ( 0 0 ) ( 1442880 1226880 )` (rtx-pro
  `/home/ubuntu/signed-export-1114/{s81,DeepSeek_ROM}/slice_station__*/6_final.def`). The signed layout is 1226.88 tall.
- The 1226.88 value in B3z2 was deliberate: `b3z2.py` "SIGNED-FIT-AUDIT (COORD): 4 signed slice_station types were
  signed at 1226.88 but plan slot 1278.72; restore to 1226.88". `b6.py` reverses exactly that.
- Plan pins agree with the signed layout, not with 1278.72: north edge clock taps sit at y 1224.2 in t41,
  t6 cl54a9ceeb and t29 cl2e5c855a, i.e. 2.7 um under a 1226.88 edge and 54.5 um under a 1278.72 edge.

Lane check:
- S81-LEAF-PLAN 20:24 handoff: "35 signed slice_station rows stay on 92e2: keep that restore in the merged B6".
  B6a breaks that for 4 rows.
- DIE-S81-92's own 19:25 scope: "B5/B6 re-key NO SIGNED slice_station type". Against B3z2sc2 these 4 signed blocks change.

Consequence: the plan would say the four seams abut while the signed macros stop 51.84 um short. At die assembly the
22 lane ports on those seams are open, or need die wires through a strip the plan counts as station area.

Fix for B6b (pick one, both keep the truth in the plan):
1. Keep 1226.88 and declare the 51.84 um strip as a die channel with pin-to-pin jumpers for the 22 ports (about 52 um
   of wire, no cycle). Zero re-sign.
2. Re-key the four to 1278.72 with north pins on the new edge and re-sign them (owner 11-12: re-sign is fast). 4 builds.

Inference: s_7N_x13 (t51, unsigned, 1278.72) shows the same pin-at-1224.2 pattern, so the slot-versus-pin mismatch may
be a class of the 1278.72 stations, not only of the four signed ones.

The 2 pg_domain fixes are right: both io windows now equal the domain `bumps.exclude_um` (y shift -544.32).

## F2. Signed re-key (advisory)

- Serdes x11: no S81 serdes type is in the signed INDEX (0 rows). No re-key. The signed inner core `ot_s81_kp4_dchn`
  is untouched: TXPIPE/RXPIPE/RST_TREE appear only in `ot_pdie_serdes_col.sv`.
- `OT_S81_GUNIT_FWDOWN` is a global elab define and changes `dsdv_gunit_l1f.sv` (NW 9 -> 24, NR 13 -> 21, both modules).
  Signed cores `dsdv_gunit_l1f_ba0` and `dsdv_gunit_l1f_ba1` no longer match the bound RTL: 2 signed records are stale
  until the g4 form signs off. COORD already ruled g4 counts; TYPE-GUNIT-L1F owns it. g4 was in GRT at 19:50.
- Leaf `ot_s81sl_vp.sv` 2488b31ca49a is NOT new in B6a: `ovl_b3y` and `ovl_zk2` (the B3z2sc2 overlay) hold the same sha.
- The four outline rows: see F1.

## F3. Serdes latency rows (advisory)

- Rows are self-consistent: 14 TX lanes (WN0-3, WS0-3, EN0-3, ES0-1), fixed 0 -> 1, cycles and natural +1. The 14 RX
  lanes are untouched (they already had fixed 1).
- But `fixed_cycles` is landed by the bind as its own pad stage (`kit_istations.py` line 4, `lane_asbuilt_latency.py`
  receiver rule). It does not price the `u_txl` row. Proof: B3x2b LATCHECK passed 873/873 with TX lanes at fixed 0,
  dst_lpad 0, while the column already held 2 unpriced `u_txl` rows.
- So TX grows by 2 registers: one bind pad (in the table) and the TXPIPE row (link internal, not in the table).
  LATCHECK will pass by construction and says nothing about TXPIPE.
- RXPIPE is +1 on pma_rck before the rate matcher; no table row. Inference: correct, the rate matcher and idle
  skipping absorb it, as the file header states.
- B6b: drop `fixed_cycles` on the 14 TX lanes (rows -1) unless the extra face stage is wanted for timing. Saves 14 lane
  pads and one cycle. Not a failure either way.

## F4. gen_phys.py overlay patch (complete)

- `ovl_b6/tools/die_plan/gen_phys.py` (280cdda75bac) versus `ovl_zk2`: exactly the three edits of SERDES-TXPIPE
  `p_gen.py`: SERDES_PIPE_CHAINS, the new `txl_mid_exports(..., defines=())` body, and the call at line 5289. It parses;
  `type_verilog_defines` exists (line 5749).
- `txl_mid.tcl` 55910a60e3cc and `ot_pdie_serdes_col.sv` 1d37c3ebeec6 equal the SERDES-TXPIPE overlay byte for byte,
  in `ovl_b6` and in `run/b/B6a/src`.
- Caveat: the bind does not generate kits. Wave and private serdes kits need the same three files in their own
  generation tree.
- To check on the first serdes kit (inference, not measured): plan `verilog_defines` for serdes are
  OT_KP4_DEC_HARD + TXPIPE + RXPIPE, without OT_S81_SERDES_RST_TREE, which the elab has globally. Confirm the kit
  `config.mk` VERILOG_DEFINES carries RST_TREE through the kit-rtl defines.

## F5. Bind dedup risk (OPEN: no bound output yet)

Preconditions verified:
- `run/b/B6a/src` holds col.sv 1d37c3ebeec6, vp.sv 2488b31ca49a, txl_mid.tcl, gen_phys.py from the overlay.
- `asbuilt_run.json` base = `run/b/B6a/src`; defines include all four DEFS_ADD; `files` lists the col, vp and l1f paths.
- No ELAB_FROM; `asbuilt.json` is removed before a fresh elab.

After BIND_RC, DIE-S81-92 should post these greps of the bound output:
- `u_rxf` present and `u_txl` at N = 3 in every `s81p_serdes__t*` module;
- the FWDOWN form of l1f (24 `g_wq` groups, 21 reset regions);
- `OUT/asbuilt_sources.json` sha of the three RTL files equal to the overlay.
Inference: `OUT` is seeded from the r12bA bind (`lint_merged`, `native_internal_stations`, `parameterized_interfaces`
kept); if those caches are keyed by name rather than hash they can carry pre-overlay content.

## F6. What B6b must still carry

From the launch line: col C1 and C2 (core taps, u_d7_6_Y replicate), C4 lpad fold, leaf landing, kv_leaf core taps,
landing-ring densify (iqf, eng, seqhost, bk_sel), p6 M8 grant, svc v2g + dsdv_idx_rg2 + OT_SVC_ATT_MEM_MACRO, M9,
serdes clock island + balance 450 + u_chn tap, RXNEG.

Missing or in conflict:
- S81-LEAF-PLAN B6s merge: the leaf delta (114 types) is built on B3z2 92e2f585dc06, not on B3z2sc2, and requires the
  signed station rows at 1226.88. It conflicts with B6a on the 4 rows of F1. Re-stage the LF_CS netlist on the merged plan.
- F1 fix and the F3 decision.
- The two stale signed l1f cores (F2) need the g4 sign-off before the count is quoted.
- Kit generation tree needs the F4 files.
