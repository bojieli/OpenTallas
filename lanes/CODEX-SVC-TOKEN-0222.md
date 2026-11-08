# CODEX SVC and token takeover 2026-11-08 02:22 PST

CODEX took over S81 R5 H8 compiler/RTL and all token lanes. No merges, tags or plans of record changed.

## Current coverage
- SVC RTL: child svc_rtl collects predecessor uncommitted 9 files + 4 H8 role includes from epyc4 /srv/opentallas-scratch3/claude/s81-svcrs-3/repo to own codex branch. Stale SE/SO and SOT pass filtering diagnosed; fixes underway before proof.
- Compiler: own branch codex/svc-compiler-0222 on epyc4 /srv/opentallas-scratch3/claude/codex-svcc-0222/repo, based on 547d04faa6. Corrected stale P.V packing to match 02:10 RTL interface: each of 4 data words carries 8 heads in low256; high256 zero. Tests via ot-run on epyc4. H8 engine latencies remain uncalibrated until RTL bench.
- Token: child token owns all dies' token/model lanes; previous token jobs terminal. HEAD calendar omission/+15 and LEP coll0+2 obligations being inspected on own branch; DS47/HWIN/globalHOST-KS-reset and Qwen programme/leases remain open.

## CODEX notes
- Prior per-pass SO failed job-gate done-before-final-q-frame. Latest interface uses one landing + two SE/P.V passes + one final SO programme and one all-head SOT booking. No duplicate HBM/ROWS traffic.
- Predecessor compiler commit exists locally: 547d04faa69336579a178eb5608fffe66e10d4d5, despite latest queue saying not yet pushed. Preserved intact.

## Next
Finish compiler packing gate, publish own branch, integrate H8 RTL proof constants, price service span in downstream calendar, collect token calendar repair. No physical launch before review and proof.

### Compiler result
19/19 H8+compressed compiler checks PASS after restoring sparse svc_routes fixture. Initial NOT RUN cause was isolated Python excluding user pytest; rerun used explicit pytest path. Real L0 H16 base/tip identity PASS: schedule/q/PV digest d8dad1f15035653f96c1cce6301a2dba5a1a79a515cdfc988da26911741b170d, 818 q words, service span3138cycles. H8 diagnostic span3986 (+848) is INVALID as a release price: RTL investigation finds fold produces1Pword/2cycles while engine consumes2words/cycle, so zero-frame-lag PO needs correction. H8_CALIBRATED remains false. ProductionT128 calibration active with RTL child.
