# KV event27f native provider source review, 2026-10-29
Picture: results/geom_review/codex_kv_provider_1029.png (viewed by Codex).

PASS-COND for all-cell source import. The full die follows the existing neighbour graph around hard cores; dense windows show the FF and combinational bodies packed in the existing white islands, alongside green clock cells, with no grey M1 obstruction or red hard-core body intrusion. Native endpoints use the exact event27f pin sites. All 22,671 mapped bodies fit with zero native-clock/hard/soft-OBS/new-body collisions; maximum node-anchor displacement is 10.55 um. Clock topology and connections are unchanged; retained legal R0 homes are used.

No additional islands or macro channels are carved. Existing macro halos/clock corridors remain. Full pin-to-pin graph reach is checked after source import. PG continuity and actual loaded clock/reset phase are still open; no routed timing, IR, signoff or freeze conclusion is made by this source-import review. Do not submit signal routing/STA until those source obligations are met.
