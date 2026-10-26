# PATH-FREEZE -- die-gate state + interface freeze per path (closure order, owner approved 2026-10-25 18:45 PDT)
# One line per update: PATH | gate item (GRT0 / CLOCK-ROUTE / PATH-STA) | PASS/FAIL/RUNNING | evidence (run dir, commit, flow tag) | date
# On all three PASS: "FROZEN <path> plan@sha" -- after that, interface changes only via lanes/PLAN-DELTA.md daily batch.
S81   | GRT0 | FAIL (FT G0C222; t14/t58 G2 FAIL) | see PATH-S81.md | 2026-10-25 18:45
QC    | GRT0 | NOT RUN on current plan | - | 2026-10-25 18:45
KV    | GRT0 | NOT RUN on current plan | - | 2026-10-25 18:45
HBM   | GRT0 | FAIL (2740 north route macro wall) | see PATH-HBM.md | 2026-10-25 18:45
CLOCK | E5 die clock route | FAIL (S1 slew, S2 early macro clocks, GRT-0229, M6/M7 overflow) | see CLOCK.md | 2026-10-25 18:45
KV    | GRT0 | FAIL 816,190 (M6 418k/M7 398k, all W column: hg_WN|hgi_WN seam corners at every row boundary, hgi_WN_4/5 N face ft4, io_W3 S, hub_Wo/Wi) on main plan e6326d34 (main 20b4554a0f, it5) | DIE-FT epyc1:/srv/opentallas-scratch2/claude/die-ft-1830/qwen_kvsys/{ovf.json,ovf.png}; fix = KV delta (c) N-S ft window spread on hgi N/S faces + hgi_v8 W/row channel split, plus sys_c F1-F3 (claude/path-kv-sysc2-1025@becb8f371d, GEOM PASS-COND 18:43) -> PATH-KV re-probe with DIE-FT | 2026-10-25 18:46
KV    | CLOCK-ROUTE / PATH-STA | NOT RUN (blocked on GRT0) | - | 2026-10-25 18:46
