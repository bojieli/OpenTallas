# QC tap-density continuation

2026-11-06 06:21 PST: codex/qc-tapsplit-1106@2384966839 candidate event pushed, parent qc_head and merge notified. Active POR and clock contracts unchanged.

Own workspace E5 dedicated scratch2 `/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106`; source clone388MB borrows Git objects from predecessor scratch3 `qc-tapsplit/OpenTallas/.git/objects`, protected while continuing. All jobs terminal; no CAD/P&R launched.

Measured proposal and actual viewed image are committed under `physical/die_plan/qwen_compute/tap_split_1106`. Soft sinks SUc36622, CBN52809, CBF59574, ST_A72232/72166; proposed taps74/97/121/125/125, max actual loads1026/1049/924/1078/1200, max reaches193.184/197.148/170.612/185.086/185.086um. Existing planned inventory missed actual concentrations despite already declaring density/max1200. Complete bins replace the lower-bound inventory; source windows/insertion targets unchanged.

Do not count this as hold closure or an adopted grid. New clock ports require coherent parent/native/reset/START/provider integration. New hardened-ring parents need their own current soft inventory/obstacles, not this old soft-ring profile.

Next bounded B: per-bit adjacent-chain affinity constrained to a local tap/radius/capacity, rather than whole-station grouping (which can exceed1200 or span mm). CBN5658 bit chains:4224 fit ideal L1radius<=200,1434 do not; CBF5144:1399 fit,3745 do not. Long crossings still need ordinary hold repair or explicit priced safe stages. No SDC false-path or tap-window reduction.

2026-11-06 07:06 PST: B default-off shared support READY `b5cd6c464a` on same branch (code d63/953/a3), parent/merge notified. Exact per-bit/scalar generated-delay groups include terminal q; source identity excludes hard/gated/mux/inverter descendants and refuses changed instance/master. Radius/group/cap bounds strict. Twelve focused Tcl/plan positive and negative checks PASS.

Actual E5 scratch2 in-memory97tap CBN prototype completed unit `oth-ubuntu-3851586-1793977217`, exit0, outputs ownroot/canary_cbn_97. 36,004 eligible direct positive register CLK pins /8,228 groups; 5,302 bounded chain segments joined,15,544 CLK pin moves,2,930 already same tap. Full comparison PASS:348,544 instance/master/pose records and1,288,379 other pin/net records unchanged; finalmaxload1200 andmaxjoinedreach199.990um. Exact actual groups retained `ot_tap_chain_groups.tsv`; compact results/scripts/image committed `tap_split_1106/affinity_event`. Actual image viewed PASS-COND assignment only; no CTS/PG/hold/native credit. Old28tap A/B control did0legalmoves atcap1200/max4814, confirming measured density A prerequisite. All finite jobs terminal; no private P&R launched. KV clock owns independent actual PV canary using same helper. Coherent parent/native/reset/START/provider adoption and fresh hardring geometry census remain parent-owned.
