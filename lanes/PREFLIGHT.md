
## 2026-10-27 10:44 PDT PREFLIGHT-2 result
READY claude/preflight-2-1027@db1eb4c5e (base main 60b5ddf52). PREFLIGHT-1 left only an unmodified sparse worktree (no commits); continued there.
- tools/die_plan/kit_contract.py: 10 static checks (no synth/place, <1 s/kit): corner_modes, ff_binding (TT 250/FF 202.5), clock_pin_geometry (M5 track + >=0.048x0.48 in io.tcl AND core_infra procs/calls; pins.json mismatch = warning only), rc_calibration (FLOW-RC-1 check_rc_cal records, local copy of claude/flow-rc-1027@2bbe885e4), duplicate_modules, keep_hook (+$paramod rename), pins_canonical (GATE-PINS-2 sha of io.tcl placed set == freeze pins_canon_sha256 [+ plan file when reachable]), mesh_vias (DCM.mesh_via_findings), macro_channels (>=10.8 um both sides per column + interior H channel per stack), clock_entry_clear. A check that cannot run = FAIL.
- kit_preflight.py v2 runs them; BINDING on hard-core kits (core freeze schema / core master_slice / core.json), advisory on partition kits (--contract forces). Writes <kit>/preflight.json beside freeze.json (excluded from KV/HBM kit_hash); --out receipts unchanged.
- Admission hook: autopilot signoff_chain already execs the immutable admission bundle's die_plan/kit_preflight.py (main f108b501fd), and gen_phys run_kit.sh runs the kit copy pre-floor -> both pick this up on merge; signoff.py bundle deps + kit_contract.py/die_sta_related.py. ot-run itself (~/.local/bin/ot-run, not in repo) NOT changed. AUTOPILOT-SIGNOFF-2 coordination: no code change needed on its side.
- Tests: test_kit_contract.py 16 PASS (fixture passes all 10; 11 mutants each fail only their check); existing test_static_preflight/test_kit_preflight/test_signoff/test_master_slice 104 PASS, autopilot test_signoff_chain 11 PASS (CHECKED, localhost sparse).
- Sweep (CHECKED, read-only, no preflight.json written) over 72 existing queued kits on intel2/epyc2/intel1 (274 epyc1 rows dead): 72/72 FAIL. Every kit FAILs rc_calibration (no '# OT_RC_CAL signal/clock' records: FLOW-RC-1 not on main yet -> merging this BEFORE FLOW-RC-1 blocks all admissions; merge FLOW-RC-1 first or together). pins_canonical FAIL 69/72 (pins_canon_sha256 recorded only in KV-CORES kits; 8/11 recorded KV kits match on io.tcl; kv3_head_eighth_e1/e5 r26 + pv_join fR180 mismatch UNCHECKED cause). clock_pin_geometry FAIL 51 (QC pushdown.tcl 0.024x0.384, io.tcl 0.024x0.084, S81 c15b core_infra 0.032x0.192 off-track = the DRT-0255 class, M3/M4 entries). corner_modes 17 / ff_binding 22 (QC prog/btab/vmr contracts 452-520 TT, S81 eh1 258.53, HBM idx_score no insertion_ff_ps). keep_hook 10 (CLOCK-RESET col_h10 kits: keep regs, no SYNTH_CANONICALIZE_TCL). macro_channels/clock_entry_clear 5 (HBM/KV macro kits with no MACRO_PLACEMENT_TCL -> placement not static -> FAIL closed). duplicate_modules 0, mesh_vias NA (no mesh inputs in core kits).
Per lane (kits / FAIL checks besides rc_calibration):
  CLOCK-RESET: 9 kits (1 core); only-RC-FAIL 0; clock_pin_geometry 9, rc_calibration 9, keep_hook 9, pins_canonical 9, ff_binding 1
  CODEX-S81: 3 kits (3 core); only-RC-FAIL 0; clock_pin_geometry 3, rc_calibration 3, pins_canonical 3
  CORES-KITS: 3 kits (3 core); only-RC-FAIL 0; clock_pin_geometry 3, rc_calibration 3, pins_canonical 3, ff_binding 1, macro_channels 1, clock_entry_clear 1
  FLOW: 1 kits (1 core); only-RC-FAIL 0; corner_modes 1, ff_binding 1, clock_pin_geometry 1, rc_calibration 1, pins_canonical 1
  HBM-CORE-LAT: 3 kits (3 core); only-RC-FAIL 0; rc_calibration 3, pins_canonical 3, clock_pin_geometry 1, macro_channels 1, clock_entry_clear 1
  HBM-KITS: 1 kits (1 core); only-RC-FAIL 0; ff_binding 1, clock_pin_geometry 1, rc_calibration 1, pins_canonical 1
  KITS-WAVE: 1 kits (1 core); only-RC-FAIL 0; clock_pin_geometry 1, rc_calibration 1, pins_canonical 1
  KV-CORES: 10 kits (10 core); only-RC-FAIL 0; rc_calibration 10, pins_canonical 10
  KV-KITS: 2 kits (0 core); only-RC-FAIL 0; clock_pin_geometry 2, rc_calibration 2, pins_canonical 2
  KV-unqueued: 3 kits (3 core); only-RC-FAIL 0; rc_calibration 3, macro_channels 3, clock_entry_clear 3
  PATH-KV: 1 kits (1 core); only-RC-FAIL 0; clock_pin_geometry 1, rc_calibration 1, pins_canonical 1
  PATH-QC: 9 kits (8 core); only-RC-FAIL 0; corner_modes 9, ff_binding 9, clock_pin_geometry 9, rc_calibration 9, pins_canonical 9, keep_hook 1
  PATH-S81: 1 kits (1 core); only-RC-FAIL 0; clock_pin_geometry 1, rc_calibration 1, pins_canonical 1
  QC-CORES: 2 kits (2 core); only-RC-FAIL 0; clock_pin_geometry 2, rc_calibration 2, pins_canonical 2, ff_binding 1
  QC-CORES-CODEX: 11 kits (11 core); only-RC-FAIL 0; clock_pin_geometry 11, rc_calibration 11, pins_canonical 11, corner_modes 6, ff_binding 6
  S81: 2 kits (2 core); only-RC-FAIL 0; ff_binding 2, clock_pin_geometry 2, rc_calibration 2, pins_canonical 2, corner_modes 1
  S81-CORE-LAT: 10 kits (10 core); only-RC-FAIL 0; rc_calibration 10, pins_canonical 10, clock_pin_geometry 4
Full per-kit list: intel2:/srv/opentallas-scratch2/claude/preflight-2-tools/sweep_*.json is NOT kept; per-kit summary copied to intel2:/srv/opentallas-scratch2/claude/preflight-2-tools/summary.txt.
ASKs: (1) MIN_CHANNEL_UM 10.8 adopted from HBM-MU-QUAD-6 ASK 07:52 (unruled; abutted pairs count as no channel). (2) unplaced macros (ORFS auto macro place) FAIL closed - confirm or require MACRO_PLACEMENT_TCL in HBM/KV generators. (3) merge order vs FLOW-RC-1.
