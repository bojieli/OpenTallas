# HBM selector hist double-driver fix (HBM-CORES-KITS-11, 2026-10-29 06:24 PDT)
Failure: selector procsplit kit (unit 409934) FAIL_PREFLOOR rtl_lint, 3584 multiple-driver bits = 4x64x14 hist[q][b].
Root cause: with STRUCT=1 the per-bin generate processes drive hist, but the shared per-quarter process still
assigned hist under runtime if(!STRUCT) guards, so Yosys proc kept a hold-only $dff per bit there (second driver).
Fix: the legacy hist writes move into a generate else-branch (legacy_hist) of bounded_hist, own process, same clock,
reset and statement order. STRUCT=0 logic unchanged; STRUCT=1 has one driver per hist bit. No port/state/edge change.
Proof (intel2 /srv/opentallas-scratch2/claude/kits11-1029):
- rtl_lint (kit rtl_lint.ys, kit fshell STRUCT=1, new source): PASS errors 0, 245 s (old source: FAIL 3584, >36 min).
- lockstep vs canonical ot_hbm_idx_selector_static (tb.sv + SSTRUCT param, tb_sstruct.diff), STRUCT=0 and 1:
  full PASS 8079 cycles / 1018 selected beats / 0 mismatches (both), tie PASS (both),
  threshold mutant MUT=1 CAUGHT (both), op8 fault mutant MUT=3 CAUGHT (both). run_sim.sh, *.tail.txt.
