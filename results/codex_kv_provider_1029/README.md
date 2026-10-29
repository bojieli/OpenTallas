# KV event27f: native all-cell provider import

The previous clock/FT route source omitted all 331 native START/reset boundary ports. Its old provider placement also used clock names without `ck_` and 32 different clock homes, so its preflight correctly refused import.

`prepare_source.py` appends only the exact event27f declared partition landing pins/nets to a fresh copied source kit and combo. It creates no external input/test driver. `bind_native_source.py` checks actual native endpoint directions and drivers and connects all 331 provider ports plus 1,528 stage clocks; it retains the legal R0 body pack of the same 15,296 clock cells, preserving their exact connections. This is a new physical source requiring new loaded routed timing.

The fresh all-cell placement treats every actual M1-M3 OBS, clock body, hard-core rectangle and lower PG shape as an obstacle. All 22,671 cells fit the already-open islands, with no additional OBS cuts, zero overlaps and maximum node-anchor displacement 10.55 um. The initial two soft-OBS hits are preserved in `proposal_native` and were repaired by the stricter `proposal_open` placement. The rendered geometry was viewed before import; review is `results/geom_review/codex_kv_provider_1029.md`.

Actual import: 10,530 FF + 12,141 combinational cells; 45,342 PG terminals exported. All 15,456 native instances and connections and 185,838 existing net-route snapshots remain unchanged through import. Actual ODB pin geometry reaches: 14,940 internal + 174 native input + 157 native output registered paths, maximum 355.326 um, zero over 405 um. This is geometry and source assembly, not a timing or signoff conclusion.

Runtime on intel1: `/srv/opentallas-scratch2/claude/codex-kv-0822`. Current physical source `imported/provider.odb`; PG and loaded clock interfaces `imported/provider_pg_terms.json` / `clock_loads.json`; complete bindings `native_bound/bindings_native.json`. The input plan `plan_e27f.json` is the existing DIE-KV-29 event27f gate-fix plan; provider inventory/mapped source are the retained native6 design, with no RTL or cycle changes. Scripts and compact receipts here preserve the executed step. The shared importer/placer are retained in runtime `imp/`, originally `codex/provider-import-1029`.

Next: actual provider M1 rails and PG joins (KV-PG helper), loaded routed clock/reset timing and signal GRT, strict bind27f result, then core-free kits and real-view die STA. Old e27f GRT0 used an unpopulated source and is not a result for this new loaded source. No release/freeze or SIGNED claim.
