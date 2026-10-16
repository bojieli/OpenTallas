# S81 network native successors, Codex23:30 takeover

The initial native-only recommendation was held when strict bundle hashes exposed a shared postprocessing provenance defect. `recovered_successors_0010.json` and each view's `provenance/` now record strict raw-final-ODB replay and exact historical helper replay for these15 plus stnv566f9. Raw LEFs match immutable original manifests, processed outputs match published LEFs, original geometry remains, and strict export_fix passes. Root review/publication remains required before adoption; no physical route or timing library changed.

Audit source `ee0e208ef119e6bc7a43cd6e5facda21f2d9631a`. Actual TT exported pins use launch220ps/capture190ps/spread80ps limits. All15 successors below pass with insertion records. Each full route has TT setup/FF hold >=0 and DRC0 in its CLOSED record. Floorplan and density PNGs were read after verdict.

| Master | Launch ps | Capture ps | Spread ps | R ps | View |
|---|---:|---:|---:|---:|---|
| dsfd_rly_283_EW | 199.0 | 124.1 | 7.7 | 83.5 | `physical/ref_tile/s81_rly_283_ew/views/dsfd_rly_283_EW` |
| dsfd_rly_283_SN | 203.1 | 104.7 | 4.5 | 85.3 | `physical/ref_tile/s81_rly_283_sn/views/dsfd_rly_283_SN` |
| dsfd_rly_283_WE | 193.1 | 103.3 | 3.4 | 83.7 | `physical/ref_tile/s81_rly_283_we/views/dsfd_rly_283_WE` |
| dsfd_rly_63_SE | 182.8 | 102.5 | 2.8 | 59.8 | `physical/ref_tile/s81_rly_63_se/views/dsfd_rly_63_SE` |
| dsfd_rly_63_WE | 182.8 | 99.3 | 1.3 | 60.8 | `physical/ref_tile/s81_rly_63_we/views/dsfd_rly_63_WE` |
| dsfd_rly_63_WN | 185.5 | 98.6 | 2.7 | 60.7 | `physical/ref_tile/s81_rly_63_wn/views/dsfd_rly_63_WN` |
| dsfd_rly_63_WS | 182.6 | 100.3 | 2.0 | 60.9 | `physical/ref_tile/s81_rly_63_ws/views/dsfd_rly_63_WS` |
| dsfd_rly_66_ES | 178.1 | 109.4 | 1.4 | 60.2 | `physical/ref_tile/s81_rly_66_es/views/dsfd_rly_66_ES` |
| dsfd_rly_66_WS | 181.9 | 120.3 | 1.0 | 60.7 | `physical/ref_tile/s81_rly_66_ws/views/dsfd_rly_66_WS` |
| dsfd_node_LLd | 166.9 | 138.4 | 17.3 | 109.7 | `physical/ref_tile/s81net_node_lld/views/dsfd_node_LLd` |
| dsfd_node_LLfd | 176.9 | 139.9 | 7.4 | 108.3 | `physical/ref_tile/s81net_node_llfd/views/dsfd_node_LLfd` |
| dsfd_node_LLfu | 170.1 | 149.1 | 17.5 | 111.0 | `physical/ref_tile/s81net_node_llfu/views/dsfd_node_LLfu` |
| dsfd_node_NNfd | 178.7 | 143.9 | 14.2 | 110.5 | `physical/ref_tile/s81net_node_nnfd/views/dsfd_node_NNfd` |
| dsfd_node_NNfu | 178.8 | 158.5 | 25.1 | 112.0 | `physical/ref_tile/s81net_node_nnfu/views/dsfd_node_NNfu` |
| dsfd_sstn_e0c0sinf | 180.7 | 172.5 | 16.4 | 114.3 | `physical/ref_tile/s81net_sstn_e0c0sinf/views/dsfd_sstn_e0c0sinf` |

Nodes n6 use43.2x77.76um strips, reset-pin release adds1edge only, normal data timeline remains existing PIPE_C10. Relays r4 use RSREG=1, likewise reset release+1edge only; data registers unchanged. sstn moves fault capture to its actual pin without adding a normal data edge. These changes require exact generator flags, not aliasing old RTL to new views.

Visual findings: nodes fill slim strips without macro slivers; relay leaves retain pin-driven whitespace and edge register groups. The slot station remains a172.8x30.2um pin-bound strip, 8.9% standard-cell fill, with rows near N/S; this is a leaf, not proof of parent fill. Closed views stand.

Remaining current defects: xstg515 has515 cw-domain input captures up to355.988ps; its saved23:26 CTS gate changes no source and alone does not justify reroute. r2l1024 ha_SW insertion record has CLOCK_INSERTION_FAILED and ETM clock spread1748.8ps, so it is unauditable and cannot be bound as native PASS. cfg7_seq is owned by the compiler/control stream. Old negcap/historical views and nonstandard relays remain recorded; use source-evidenced standard rebinds rather than per-width reroutes.

191 views present in predecessor sparse checkout from historical217-view manifest;26 older assembled/variant views absent. Historical views retained and failures not treated as current-master failures.

JSON stores SHA256 of each successor Liberty/LEF/insertion/abstract and all191 observations. Images retained under `/home/ubuntu/artifacts/s81-network-2330/layouts`.
