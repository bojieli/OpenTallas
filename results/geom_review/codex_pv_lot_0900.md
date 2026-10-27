# PV join proposed family pin/lot repair

Source predecessor ac705a7e81 is retained historical proposal. Final immutable `out_dataflow/pd/cores/pv_join_pins*.json` refines only face chunks: ts0 all S; ts1[0:447] S and [448:1023] W; ts2 all N; ts3[0:95] W, [96:575] E, [576:1023] N. Whole32-bit chunks, numeric order, no RTL/cycle change. Actual pinned core_conns confirms 10 normal PV types have ts0/1 producers south, ts2/3 north. Six n variants require explicit fresh-binding alias trace before any claim covering those variants.

All3 views rendered and personally viewed: PASS pin window <=60 pins/10um, native single face layers, no corner rollover. R0 E994/W681/N1472/S1472 with peak60/41/58/58. Global clock/reset entries unchanged; 259.2x172.8 body and160 parentclock relocation ledger remain exactly predecessor ac705. Quarter-grid internal clock is model-only; no new physical build or timing signoff.

Whole geometry remains BLOCKED. Full R26-based G0 found154 actual-bit station slot collisions after anchor-only repair plus2 unresolved io-sidecar dependencies. An exploratory owncopy moved211 station groups,18 still need coupled moves; this is not released and not committed as finalplan. CLOCK-KV now supplied a newer200-slot current capsule: repairs must apply to that exact source, replacing stale R26 anchors. Original172.8 pin-density FAIL and withdrawn autopilot rows remain preserved. No route release.

## Current capsule correction, 09:57

Exact cbdc30e7ad physical/die_plan/qwen_kvsys/die_plan.json supersedes old R26 FT geometry. It has176 actual PV-overlapping bit cells in88 stage groups. Repair ledger e588624b3a translates127 existing groups, with no stage/slot count change, first and last interior groups fixed, all actual cells on .054x/.27y grids. Rounded-grid census:0 hard-core overlaps,0 station-cell overlaps, changed-slot worst adjacent-bit hop404.136um. Render `pv_current_ft.png` personally viewed: repaired cells remain outside expanded join bodies, channels retained. These results release only this physical-station delta for folding into CLOCK-KV; final whole geometry and route remain pending current clock resite/G0.

All6 nvariant fresh bind4 source5c7 RTL artifacts are now traced:96 join-input pairs match exactcbd plan physical pair aliases and position. ts0/1 producers south and ts2/3 north in all4groups for eachtype. `pv_n_trace_verified.json` records exact artifact SHA256, bit source pairs, producer body and position; the earlier six-alias pending flag is resolved. Thus all16 PV family variants have source-facing pin refinement confirmed, with no RTL/cycle change.

## Transformed face correction, 10:05

Final physical-orientation audit catches six ntypes use MX hard-core placement with the R0 pinfile; local R0 ts0/1 S would become actual N. Normal types existing fMX/fR180 pinviews transform correctly. REQUIRED coherent plan delta: all24 joins in6ntypes switch `cores/pv_join_pins_event27.json` to EXISTING `cores/pv_join_pins_fMX_event27.json`, retaining MX/body/clock/reset entry. Exact old/new ledger `pv_n_pin_view_delta.json`. Then actual ts0/1 face S and ts2/3 N match all16type producer traces. This adds no view/cohort, RTL or cycle. CLOCK-KV notified before final freeze; pending until adopted, so no claim of completed whole geometry.
