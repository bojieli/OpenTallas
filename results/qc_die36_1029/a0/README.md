# DIE-QC-36 / A0 (sub-agent of DIE-QC-36), 2026-10-29

COORD ruling [DIE-QC-35-PARK] (2): opt-in `tools/die_plan/core_infra.py` delta + A0 NL/NK plan-built tile trees + CTS on
copies of the GEOM-59 PASS-COND places (no re-place). Branch `claude/die-qc-36-a0-1029` from origin/main `49d8a0c889b`.
Spec: `claude/die-qc-35-a0-1029:results/qc_die34_1029/a0/README.md` §5-§6.

## 1. core_infra.py delta (shared tool, opt-in)

| item | field(s) | behaviour |
|---|---|---|
| (i) | `core_tree.stage_basis: total` + per-leaf `cts_stages` | already on main (DIE-KV-14b); unchanged. A0 declares `cts_stages: 3` on every FF gated domain (514..2849 sinks). New unit test on the A0 census shape. |
| (ii) | leaf `early_tap_ps {TT,FF:{min,max}}` + `early_tap_view` (receipt); tree `early_tap_stage_ps {TT,FF,source}` | a planned **macro** leaf (e.g. below a form-C planned-domain macro hop ICG) counts its macro-view insertion as k = round(mid / stage_ps) stages; k must agree at TT and FF; depth + k joins the equal total-stage check. Only with `stage_basis: total`; refused on CTS-open / gated-domain / register leaves; a stage model without any early leaf is refused. Compiled plan records `core_tree.early_taps` (k, view, residual ps). |
| (iii) | `core_tree.install_stage: pre_cts` (+ optional `late_dpl_max_um`, default 20) | tree lines and tree cells leave `master_core_infra.tcl` (pre-GPL) and go to `master_core_infra_late.tcl`; `install()` also copies the new `core_infra_late.tcl` procs; `kit_cts_hook` chains `source /work/master_core_infra_late.tcl` right before `core_infra_cts.tcl`. Late procs: `ot_ci_late_cell` (create at plan xy, row/site quantised, PLACED), `ot_ci_late_gate` (gate keeps its placed xy; plan xy only reported), `ot_ci_late_legalize` (ONE `detailed_placement` with every other instance held FIRM and restored; max displacement bound; planned cells then FIRM). Refused with gate copies, `post_place_rebind`, or frozen `cell_placements`. |

Default (no new field): code path unchanged; the tree emitter was factored into `_tree_lines()` and the NDR line into
`_ndr_line()` (pure refactor). `core_infra.tcl` / `core_infra_cts.tcl` are NOT edited (new procs live in the new file).

## 2. Estimate before build (written before the CTS launch, 13:07 PDT)

Plan stage model = `clk_aocv_table_g021.json` class B mu_stage_ps: TT 36.154 / FF 27.549 ps (core tree stage).
Macro views (kit `macros/*.lib`, min/max_clock_tree_path, min..max over rise/fall): romleaf FF 190.35..256.77 /
TT 245.10..324.14 -> k = 8 (FF 8.12, TT 7.87); LSL FF 182.09..221.28 / TT 234.90..289.04 -> k = 7 (7.32 / 7.25);
NK node FF 172.95..218.83 / TT 224.03..285.76 -> k = 7 (7.11 / 7.05).
Tree (both tiles, `gen_a0_tree.py`): T = 11 total stages = the minimum the romleaf view allows (romleaf gate on R, leaf
at depth 3: 3 + 8 = 11). Trunk R..t7 (BUFx24) from the port toward the register-ICG centroid; register hop ICGs
(NL 16 / NK 17) on t7 (depth 8) + 3 CTS stages; root registers (NL 607 -> 26 leaves / NK 1633 -> 69 leaves, 23-24
sinks each) planned at depth 11 (3 bisection levels below t7); LSL (+ NK node) gates on t2, leaf at depth 4 (4 + 7).

| quantity (model, UNCHECKED) | FF | TT |
|---|---|---|
| register insertion, 11 stages | 303 | 398 |
| romleaf pin-internal flop: 3 stages + view mid | 83 + 223.6 = 306 (+3) | 108 + 284.6 = 393 (-5) |
| LSL: 4 stages + view mid | 110 + 201.7 = 312 (+9) | 145 + 262.0 = 407 (+9) |
| NK node: 4 stages + view mid | 110 + 195.9 = 306 (+3) | 145 + 254.9 = 400 (+2) |
| view spread (min..max) around the mid | +-33 / +-20 / +-23 | +-40 / +-27 / +-31 |
| hop ICG CLK (depth 8) vs register sinks | -83 | -108 |

- vs kit vclk frame: NL frame 601.9 FF / 692.6 TT -> registers ~300 ps EARLIER than the frame: input-port hold gains
  ~300 (the -172.53 class disappears), input setup at TT loses ~295 ps vs the frame (risk). NK frame 202.5 FF ->
  registers ~100 ps LATER: input-port hold expected about -100 + data delay (vs -571.84 now).
- Realization risk: the trunk is 7 BUFx24 with short wires near the port; a short-wire BUFx24 stage is ~17 ps FF
  (TritonCTS delaybuf, §5 of the spec) not 27.5 -> registers up to ~70 ps earlier than the model, i.e. macros late
  by 0..+80 FF vs registers. Macro leaf BUFx24 sits at its gate and drives the long wire to the macro (up to ~550 um,
  rp0/rp5 at y 77): slew risk on those 18/19 nets (no repeater in the plan).
- ICG enable TT setup: ICG CLK 3 stages (~108 TT) ahead of the launching registers (spec run: ~200) -> expect the
  -223.55 / -181.77 class to improve by ~90 ps, not to close (inherent to gating at depth T-3).
- Internal sibling-hop hold (spec §5: 112 ps skew between separately built hop trees): all register ICGs now hang
  from one node at one depth -> expected sibling skew = per-domain CTS imbalance (~20-40 ps).

## 3. Byte-identity (HARD REQUIREMENT) — PASS

- Unit test `tools/die_plan/test_core_infra_a0_optin.py::test_byte_identical_*` (33 cases: 5 fixtures + 28 in-repo
  pushdown slices): emit_tcl / compile / install / kit_cts_hook outputs sha256-equal to `git show 49d8a0c889b:core_infra.py`.
- Fleet regression `regress/regress_core_infra.py` (every kit `master_slice.json` found on the host; install +
  kit_cts_hook with the base vs the new tool in `python3 -I` subprocesses; sha256 of every output file + config.mk):
  **intel2 472/472, epyc2 74/74, intel1 155/155 identical** (`regress/regress_*.tsv`; by slice `die`: hbm 578,
  s81 59 (38 with core_tree), qwen_compute (QC) 50 (7 with core_tree), qwen_kvsys (KV) 14 (all core_tree)).
  No HEAD kit with a master_slice.json exists on these hosts (searched); HEAD is covered by the in-repo unit cases only.
- New tests: 22 pass (intel2 venv-pytest-hb4). Existing `test_core_infra.py` / `test_kit_cts_hook.py` pass; the 3
  `test_core_kit_gens_main_tool` failures (hbm_harden, s81_eng, s81_svc) are identical on the unmodified base worktree.

## 4. CTS on copies of the PASS-COND places (no re-place; `make -n` = do-4_1_cts, do-4_cts only)

Kit copies `intel2:/srv/opentallas-scratch2/claude/dqc36-a0/cts/{qfd_tile_nl_a0c_a0nl14icg2rr2,qfd_tile_nk_a0c_a0nk14icg2rr1}`,
fc_dt_lift_cts.tcl verbatim from kitgen `866c6a98e96`. Gate = OT_HOLD_STRUCTURAL in cts.tcl. ot-run units (intel2, `oth-ubuntu-<n>`):

| run | NL unit | NK unit | outcome |
|---|---|---|---|
| 1 | 2911297 | 2911295 | FAIL ODB-0373 connect to dont_touch `mp_a0_t7_out` inside TritonCTS |
| 2 (+ `-no_insertion_delay`) | 3045921 | 3045916 | same ODB-0373 |
| diag (dont_touch lifted, diag copy) | 3095468 | 3095969 | cause: TritonCTS clones hop ICGs (`clone_1_g_icg.g_hop.u_hop_{ck,fa2,fa3}/u_icg`) onto the parent net; `-repair_clock_nets` RSZ-3006 on `mp_a0_t2_out` |
| 3 (drop `-repair_clock_nets`) | 3135978 | 3136043 | ODB-0373 (clones) |
| **4** (accept ICG clones fail-closed on the gate parent net) | 3181331 | 3181335 | **CTS ran; OT_HOLD_STRUCTURAL FAIL** |
| hold diag (report-only copy) | 3264667 | 3264183 | worst paths + skew below |

Late install CHECKED (run 4): all hop gates kept placed xy (d=0.000: NL 34, NK 36 gates); OT_CORE_INFRA_LATE_DPL NL
61 cells max 26.14 um, NK 120 cells max 35.29 um (bound 60); TritonCTS on 16 / 17 CTS-open nets only; ICG clones NL 1,
NK 3.

Gate numbers CHECKED from cts.log (ss mode = corner tc = TT setup; ff mode = FF hold):

| tile | TT setup ws (pre / post repair_timing) | FF hold ws | failing hold endpoints | related-pair skew (report_clock_skew, diag) |
|---|---|---|---|---|
| NL | -699.01 / -616.34 ps | -654.46 ps | 5718 (limit 2000, ws >= -100) | setup 741.6 / hold -1075.5 ps |
| NK | -1351.35 / -1319.11 ps | -1105.87 ps | 7766 | setup 1235.7 / hold 1173.5 ps |

Verdict: FAIL (kept). Root cause (CHECKED in `cts/nl_diag_hold_paths.txt`, `nk_...`): the **plan**, not the tool. The
top trunk node `mp_a0_t7` (one BUFx24) drives all 16/17 register hop ICGs (+ clones) at their placed xy AND the root
register sub-tree parents `mp_a0_p8_*`, spread over the whole tile. TT stage delay on that one net: NL 60..411 ps
(ICG GCLK tx3 60, tx4 227, ck 284, tx7 310, fa2 411; t7 -> p8_0 325), NK up to 893 ps (t7 -> p8_0 741, clone fa3 893),
vs the 36 ps plan stage model. The upper trunk is short-wire (t4..t6 ~25 ps). The estimate in §2 missed this:
gen_a0_tree.py puts no span/fanout bound on the gate-parent node (core_infra checks levels/loads, not wire span).

## 5. Next step

gen_a0_tree.py: replace the single t7 fan-out by a planned spread level (H-tree / bisection of the gate + p8 load set,
<= ~4 loads and <= ~150 um span per node, same total depth T = 11 by shortening the straight trunk), re-run prep +
CTS on fresh copies. core_infra.py delta needs no change for that. Open question for the tool owner: TritonCTS ICG
cloning onto planned nets is accepted only for `install_stage: pre_cts` (fail-closed, clones made dont_touch; kit LEC
must cover them).
