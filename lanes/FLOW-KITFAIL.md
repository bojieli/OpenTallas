# FLOW-KITFAIL -- kit failure classes for the shared fixer (FLOW-KITFAIL-n). Kit lanes (S81-KITS-A, S81-CORES-KITS,
# KV-KITS-T, HEAD-KITS-T, HBM-CORES-KITS-22) append one line per failed kit run:
#   - <date> [LANE] <die>/<type> kit <host:path> stage <synth|lec|cts|grt|drt|signoff> class <short> first-line <...>
# FLOW-KITFAIL ranks by count x wasted run-hours each ~45 min and fixes shared tool/generator bugs only.

- 2026-10-29 18:46 PDT [FLOW-KITFAIL-1] CENSUS 36 h (fleet FS scan epyc2/intel1/intel2: 1312 kit run logs, run-h = stage-log span, UNCHECKED +-30%; scripts localhost ~/.claude/jobs/b7f906df/tmp/kf/{col.py,cls.py}). Ranked (runs / run-h / owner):
  1. pre-floor LEC NOT EQ / KEEP FAIL 73 / ~220 h (HBM 30, HEAD 21, S81 18, KV 2, QC 2): 42 of 49 kits ran LEC at the 4-edge default although HBM/KV/S81 die reset contracts exist -> GENERATOR BUG (only S81 legacy staged the contract) -> FIXED claude/flow-kitfail-1-1029@f82d4e1109 (READY). Rest: S81 LP + HEAD hd_host/mesh/lep/gbx/spn KEEP FAIL u_gb.g_pc[].ps[] / u_ep.rdy_k[3] merged-by-synth (persists at 64 edges, Codex LP 10-29) = one shared lane-gearbox keep/RTL class -> S81-KITS-A/HEAD-KITS-T; HEAD has no die reset contract (kp4_dchn apply[1..7] removed) -> DIE-HEAD.
  2. sign-off hold_ff (+drv/+setup) near misses ~139 / ~250 h (KV, HEAD, S81_HEAD 34, QC) -> FLOW-CLOCK-R7 (hold-pad + drive repair), not duplicated.
  3. post-CTS FF structural hold gate stop 147 / 35 h (KV 71, QC 59, HEAD 17) + GRT OT_HOLD_STRUCTURAL 78 / 66 h (HBM 75): fail-early already works; plan/boundary (die owners).
  4. setup_tt > 25 ps at sign-off ~13 / 34 h; S81 pre-route insertion gate 23 / 34 h; DPL-0033 13 / 30 h; GRT-0116 5 / 28 h; DRT-0255 7 / 21 h (kv3_pv_pair same box re-run 4x).
