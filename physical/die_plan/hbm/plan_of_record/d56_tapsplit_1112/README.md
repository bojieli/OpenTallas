# HBM tap split (TAP-SPLIT-1, 2026-11-12)

Compose-format deltas, base t36 (02659299fcf0), applied in this order with `compose.py apply`:

1. deltas/tapsplit_longhop_1112b.json.gz (sha256 of the uncompressed json: 559cd25315fdd6e0): longhop_d55 (6afe8ebde07d) plus the tap split of 51 types (clock: tap_mode grid+explicit, added_taps; q_su11__physical_v1 taps re-derived on the longhop plan). Plan sha de3584d1e3d89468. Supersedes tapsplit_longhop_1112.json (d2cb1aa08dcd66e0) and tapsplit_1112.json (90764189e6f2ed1e).
2. deltas/tapsplit_phyne_1112.json (sha256 fb12e15b8619af03): PHY_NE clock only (1 grid + 8 added taps, max 749 sinks per tap). Base: plan de3584d1e3d89468. Result plan sha 7f4896f364be72af.

G0 (xtap-sweep-1-r2, main 7b84010b1c6e, --tap-sink-cap error): g0/g0_report_t36 (before), _comb2 (after 1), _comb3 (after 2). 569 errors / 1864 warnings in all three, identical per check. tap_sink_cap taps over cap: 394 in 61 types -> 83 in 10 -> 82 in 9.
Still over cap: root, q_b010, q_b102, q_b103, q_b103__physical_v1, q_b111, q_b111__physical_v1 (sink clusters in sink_clusters_7.tsv; need a positions-only street), PHY_NC, PHY_NW (blocked by the PHY macro footprint; wait for the HBM-GEOM-2 move+flip).
