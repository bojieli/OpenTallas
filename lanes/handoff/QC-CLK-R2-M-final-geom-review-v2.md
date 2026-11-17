# Final M beaa07b778ce physical review

Image personally LOOKED: `type_focus_declared.png` (local inspected copy `/tmp/qc-clock-review/final_M_type_focus.png`).

Verdict: **FAIL** for `cbn_q00__cldbcda913` NB macro fit; the other focused panels are PASS-COND.

All five selected W515/W517 native LEFs are SIZE 140.4 BY 51.84, equal to the plan outlines. NB origin (1129.68, 2484) with track offset (0.012, 0.012) places its right edge at 1270.092, outside the type width of 1235.52 by 34.572 um. The other four landing cores fit. The north edge has spare horizontal space; physical pin and clock-entry rows must follow any actual macro move.

G changed STB x_fw_i station anchors follow open SRAM corridors. FE paths have intermediate station anchors and no hard macro wall in its glue area. The picture shows nominal per-bit bank centres, with exact bit legality covered by completed G street legalization and the one final G0 owned by the parent. The fast focus shows declared clock entries. The standard complete snapped-grid die overview remains in admitted render unit 2631585-1794899850.

This review ran no new G0, P&R or STA. Source plan SHA: beaa07b778ce233b9608c48ee0c843c59e03a1490ae57a0e917e4091d27702ad.

The earlier review.md was truncated by a shell quoting error. Its FAIL finding is preserved; this complete record supersedes its incomplete scope text.
