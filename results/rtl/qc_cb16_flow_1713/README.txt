QC CB16 legal-upstream DAG pad flow gate (Codex QC token1713 candidate 90e23102b8), RTL replay of the emitted ot_dp_dly
per-bit W1 delay lines at all 8 actual (W, D) classes: (514,2) (514,3) (514,10) (514,11) (514,15) (514,16) (516,1) (516,2).
Codex 18:2x run (intel2 codex-qc-token-1713/flow) DID NOT CONVERGE at t=0: the generated tb/ot_dp_dly had no timescale,
so the #0.4165 half period rounded to 0 (a bench packaging defect, not hardware).
Fix (bench only): gen.py now writes `timescale 1ns/1ps at the top of both generated files. No converge-limit change,
no RTL change, same dag_candidate.json (sha256 40827600a6e54e33...) and tools/die_plan/bind.py of codex/qc-token-1713
(sha256 50c6013d3fd48cd6...; gen.py reads it repo-relative and extracts module ot_dp_dly).
Result (TOK-QK 2026-10-25 18:42 PDT, ot-run intel2 unit oth-ubuntu-1451342-1792978698, Verilator 5.050,
--x-initial unique, +verilator+rand+reset+2): nominal CB16_PAD_FLOW_PASS 4096 cycles 8 classes; mutant1 (516/D1 bypass)
CAUGHT cycle 65; mutant2 (514/D16 valid one cycle early) CAUGHT cycle 67 -> CB16_FLOW_TWO_MUTANTS_CAUGHT.
Scope: delay-class RTL replay only. Not a bind, not a QC token pass, no physical credit; fresh QC bind with the phase types
(apply_cb16_phase_types.py) and CB16 alignment re-check remain the QC plan owner's gates.
