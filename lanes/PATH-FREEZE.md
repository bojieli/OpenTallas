# PATH-FREEZE -- die-gate state + interface freeze per path (closure order, owner approved 2026-10-25 18:45 PDT)
# One line per update: PATH | gate item (GRT0 / CLOCK-ROUTE / PATH-STA) | PASS/FAIL/RUNNING | evidence (run dir, commit, flow tag) | date
# On all three PASS: "FROZEN <path> plan@sha" -- after that, interface changes only via lanes/PLAN-DELTA.md daily batch.
S81   | GRT0 | FAIL (FT G0C222; t14/t58 G2 FAIL) | see PATH-S81.md | 2026-10-25 18:45
QC    | GRT0 | NOT RUN on current plan | - | 2026-10-25 18:45
KV    | GRT0 | NOT RUN on current plan | - | 2026-10-25 18:45
HBM   | GRT0 | FAIL (2740 north route macro wall) | see PATH-HBM.md | 2026-10-25 18:45
CLOCK | E5 die clock route | FAIL (S1 slew, S2 early macro clocks, GRT-0229, M6/M7 overflow) | see CLOCK.md | 2026-10-25 18:45
