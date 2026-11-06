# QC tap-density continuation

2026-11-06 06:21 PST: codex/qc-tapsplit-1106@2384966839 candidate event pushed, parent qc_head and merge notified. Active POR and clock contracts unchanged.

Own workspace E5 dedicated scratch2 `/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106`; source clone388MB borrows Git objects from predecessor scratch3 `qc-tapsplit/OpenTallas/.git/objects`, protected while continuing. All jobs terminal; no CAD/P&R launched.

Measured proposal and actual viewed image are committed under `physical/die_plan/qwen_compute/tap_split_1106`. Soft sinks SUc36622, CBN52809, CBF59574, ST_A72232/72166; proposed taps74/97/121/125/125, max actual loads1026/1049/924/1078/1200, max reaches193.184/197.148/170.612/185.086/185.086um. Existing planned inventory missed actual concentrations despite already declaring density/max1200. Complete bins replace the lower-bound inventory; source windows/insertion targets unchanged.

Do not count this as hold closure or an adopted grid. New clock ports require coherent parent/native/reset/START/provider integration. New hardened-ring parents need their own current soft inventory/obstacles, not this old soft-ring profile.

Next bounded B: per-bit adjacent-chain affinity constrained to a local tap/radius/capacity, rather than whole-station grouping (which can exceed1200 or span mm). CBN5658 bit chains:4224 fit ideal L1radius<=200,1434 do not; CBF5144:1399 fit,3745 do not. Long crossings still need ordinary hold repair or explicit priced safe stages. No SDC false-path or tap-window reduction.
