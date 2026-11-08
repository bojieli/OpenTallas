# QC SU1 production read-calendar followthrough — 2026-11-08 02:2x PST

CODEX took over: numerical requalification on codex/qc-su1-prod-0222, intel1 /srv/opentallas-scratch2/claude/codex-qc-su1-prod-0222, source 895234baeda based on b629fb69693.

Current step: run1 compile/sim admitted via ot-run24GB/4T/disk8, intel1 unit oth-ubuntu-3814669-1794133582. Controller codex-qc-su1-prod-0222-run1.service on intel2, log /home/ubuntu/coord/runlogs/codex-qc-su1-0222/run1.log. Results intel1 /srv/opentallas-scratch2/claude/codex-qc-su1-prod-0222-run1/{build.log,run.log}.

Model: true pin-to-pin providers VM6/CROM9; parent request5 + answer4 gives read roundtrip15/18. Proposed private head EXTRA9 and independent WROM compensation9, ingress4/outgoing5 => requests+9 and results+18 against unchanged zero-transport oracle. Five parallel instances: oracle, compensated candidate, WROM4 mutant, EXTRA4 mutant, uncompensated parent. No POR/default/interface or physical change.

Limits: this isolates ordinary read/reply transport. Actual lane0 request-derived WROM, VM write pad14 feedback, production scheduling and composed reset remain obligations. No whole-parent exactness or signed-off claim.

Publication: branch pushed to local source origin; push to hub failed DNS intel2 on intel1. Source remains committed, can fetch by intel1 path from hub.

## CODEX notes

Run6 prior result retained: zero-transport provider calendar PASS, not production calendar. New run1 pending.

## 2026-11-08 02:37 PST RESULT

Run1 TERMINAL PASS (ot-run exit0), source RTL/bench895234baeda, checker66b7594c8dd, final source+results2a102b5c539. 288 result words across five classes (32/64/64/64/64), VM writes64, KV writes96, actual scheduled faults40. Correct compensated form requests0/data0, scheduled fault uniquely+18 (adjacent lag17/19 each80 errors), independent BYP golden32/32/error0, warm reset leaks0. WROM4 mutant52 data differences, EXTRA4 mutant406, unchanged head under parent transport478, all request comparisons0.

Diagnosis: current read transport5+4 adds9 roundtrip edges; unchanged head has no compensating metadata alignment, so matching request addresses alone conceal wrong numeric results. Head EXTRA9 plus matching global WROM9 fixes the private read capsule. Last observed qc53v4s lane table is unchanged5/4; experiment is relevant to current candidate. Transport state6584 bits/lane before head/reset/clock overhead.

Next: actual lane0 request-derived WROM and mutable VM write pad14 feedback + compiler scheduling must compose before whole-parent adoption; neither is claimed here. No physical work launched. Source remains ownbranch; request parent publish2a102b5c539 to hub.
