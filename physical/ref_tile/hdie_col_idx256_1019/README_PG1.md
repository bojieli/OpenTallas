# hdie_col_idx256_1019 pg1 successor (LEAD2-HBM/L2H-IDX, 10-19)
Same RTL, params, outline, pin faces and recipe as the closed predecessor; only the job tag (pg1), branch and
reroute_reason change, plus tools/closure_loop, tools/ref_tile, tools/hier_contract, tools/tt_views,
tools/textbook_lint.py and physical/common_flow taken from origin/main.
Why: the closed final ODB failed the native PG audit (PG_HOLD: unbound PG ITerms, dd3920111 /
codex/hbm-idx-final-native-1019). The closure daemon now runs the PG final-connect fix (runtime 8cbc5350f,
LEAD2-HBM D3). The predecessor closure is revoked as NOT BINDABLE in revoked_closures.json; its timing history is kept.

SAFE-DESIGN checklist (owner 10-19), for a PG-only successor of a design that closed timing at TT/FF:
1 Pins: PASS (pin registers/pin-register shell and 2-stage reset landing as in the closed kit).
2 Reach: PASS (closed route; no single-cycle wire over 405 um in the closed corner STA).
3 Fanout: PASS (closed TT setup with positive slack; replicated copies unchanged).
4 Depth: PASS (closed TT setup).
5 Storage: PASS (unchanged; SRAM macros where the kit has them).
6 Floorplan: PASS (unchanged outline/util that closed GRT 0 / DRC 0).
7 Clock: PASS (closed TT/FF); io_hold_margin 0.03 -- waived for this PG-only successor:
  the geometry and hold flow that closed FF hold are kept unchanged on purpose.
8 Schedule: PASS (static; no cycle added, cycles_added 0).
