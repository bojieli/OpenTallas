# HBM-CORES-REBAL-9 (2026-10-28): lane MLAT 5 + WCOPY 1 adopted through the generators

Branch `claude/hbm-cores-rebal-9-1028` (base REBAL-8 cd8895f885, which carries the held REBAL-4 28bd43f9e1).
All new behaviour is opt-in; every default is byte-identical or elaboration-identical.

## 1. Adoption (RTL tops + compilers) -- DONE, CHECKED
* RTL (e514530414): `WCOPY` threaded pgslice -> quarter -> top -> tb_hbm_su_native_multirate_top (default 0);
  su_top_compile.py `--wcopy` (S0 +1); su_multirate_native_run.sh `SU_TOP_WCOPY` (cache key only when != 0).
* pg_lane tops (lane_full / lane_exp / lanes4): `build_split_tops.py --pg-params` (emission hook) and
  `--pg-params-existing` (rewrites the committed generated files: the as-built netlists build_split_tops reads are gone fleet-wide).
  Tops gain `#(MLAT = 4, WCOPY = 0)` and pass them to u_lane* / u_bank*. **Default elaboration == committed tops**
  (pg_default_eq.sh: yosys hierarchy, whole-design RTLIL canonicalised by body hash, rtlil_canon.py): lanes4 45 modules,
  lane_exp 56, lane_full 56 IDENTICAL. MLAT5/WCOPY1 elaboration: 5 / 12 / 12 qmul LAT=5 cells, 0 LAT=4, lat5i present, WCOPY=1 bank.
* Compiler constants through ONE generator module, `tools/hbm_static/su_lane_build.py` (lane D_* formulas, LIN,
  divider extra, side-pipe spacing, commit delay; test pins the as-built numbers and the RTL localparams):
  prod_compile.py `--mlat/--wcopy`, layer_images.py `--native-mlat/--native-wcopy` (NativeTiming mlat/wcopy;
  as_dict unchanged at default). **All 41 production SU.VOP records byte-identical at default** (pc_sweep.json).
  Tests: test_su_lane_build + native_profile/layer_images/safe_calendar/native_producer/su_bank_clock/sfu_images 11 PASS.

## 2. tok/s (current model, UNCHECKED) and token check
* Per-record compiler deltas (prod_compile's own schedule, cycles_serial, pc_sweep.json), MLAT5+WCOPY1:
  light lane records +1..+6, exp/sigmoid/SiLU/div +12..+14, rsqrt +14, softplus-sqrt +78 (side spacing 19 -> 37/element).
* r9_price.py (REBAL-8 d4g_2ring_qbg priced_layers AR baseline + those class deltas per SU record):
  base 1902.26 -> WCOPY only 1898.67 (-0.19 %), MLAT5 only 1883.66 (-0.98 %), **both 1880.14 tok/s (-1.16 %)**.
  REBAL-8's assumed +5/+7 gave -0.92 %; the measured compiler deltas (+6 light, +14 SFU, +78 spsqrt) give -1.16 %.
  Delta for DIE-HBM-10's single rerun: **-1.16 % (UNCHECKED model)**; with DIE-HBM-10 VMX -2.98 % ~ -4.1 %, under 5 %.
* Token vehicle (bit-exact, same method as TOK-ALL: su_multirate_native_run.sh, 512 lanes, MLAT 5 + WCOPY 1 via
  SU_TOP_MLAT=5 SU_TOP_WCOPY=1): vectors compiled (serial 7121 / stream 9496 edges). The Verilator build has been
  running on epyc2 (ot-run) since 11:30; the previous build took 1h50m. The chain tok_chain.sh (intel2) then runs
  POS + 6 mutants + BRIDGE_LEAF IN PARALLEL (tok_phase.sh, the same pass rule as the script; ~80 min instead of 11 h serial).
  COLLECT: epyc2:/srv/opentallas-scratch2/claude/hbm-cores-rebal-9/tok_m5w1/phase_*.res (+ positive.log endpoints),
  intel2:.../hbm-cores-rebal-9/tok_chain.log, tok_phases.otrun.log. PASS = POS PASS, 6 x CAUGHT, BRIDGE_LEAF PASS. UNCHECKED until then.

## 3. lanes__canon re-place (MLAT5 + WCOPY1) -- RUNNING
* Kit `ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77_7142128841b6-_c20ek2m_m5w1` (mk_canon_m5w1.sh: REBAL-4 c20e_k2m
  inputs, wrapper instance `#(.MLAT(5),.WCOPY(1))`, reset contract 64 edges copied). KIT_PREFLIGHT PASS 0 issues.
* CHECKED so far: synth 327,591 cells (<= 400k); FACE_GUARD PASS 3717/3717;
  **LEC EQUIVALENT 66,519/66,519 compare points, 0 differs, 0 undecided** (3941 s).
* GOAL cts on epyc2 (ot-run, --mem 32): floorplan started 12:47. Then the kit's post-CTS FF hold gate (hold_gate.tcl).
  canon_chain.sh (intel2) then runs canon_post.sh on epyc2: post-CTS TT STA (sta_cts.tcl: WNS/TNS, reg2reg, reset
  recovery after CTS, multiplier stage-1 slacks vs REBAL-8 m2 -254 / m1 -243 / e1m -214 / me2 -167 / q -118) and
  the 4_cts dump + render.
  COLLECT: epyc2:.../hbm-cores-rebal-9/canon_post/{status,sta_cts.log,hold_gate.log,cts.png}. The render must be VIEWED.

## 4. hnx_lane_x / lanes_plain / programme_store kits -- WAITING on the DIE-HBM-10 plan view
lanes_plain__canon (lanes4_core) and lane_exp__canon (lane_exp_core) take the same `#(.MLAT(5),.WCOPY(1))` wrapper
patch as mk_canon_m5w1.sh.
