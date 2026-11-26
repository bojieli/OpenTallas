# West HEAD ffbe77 detailed-placement review

**Independent visual verdict ISSUES. Keep CTS and route held.** I opened both stock images from the new final checkpoint. The two hard-pair blocks, central two-by-five SRAM bank layout, northern landing strip and right edge look the same as in the earlier image pair. The central aisles remain visible. The narrow right corridor, unsplit clock advisory and wide fanout envelope require further evidence.

| Stock check | New exact placement |
| --- | ---: |
| Opposite-facing pins | 0 |
| Peak per-face pin-track use | 0.262 |
| Peak modeled channels | 0.323 |
| Peak local standard-cell density | 0.662 |
| Unsplit core-clock centroid distance | 909.899 µm |
| Largest fanout bounding-box spread | 980.8 µm |

The visual clock measure uses the sole unsplit input against 27,737 sink endpoints. The fanout measure is led by the 269-sink `strap_ca_k_coll_i1[0]` envelope. Source preflight still flags the 4.32 µm east channel below 10.8 µm, and the detailed placement still lacks routed gate and corridor evidence. The separate no-write clock replay owns the CK5 stage disposition.

I opened a new local overlay generated from the exact final ODB. All four earlier M5 and M6 fragments are absent from their exact coordinates, and all eight continuing stripe chunks retain their bounds. The floorplan guard removed four exact pieces and zero vias. The stock rail check had zero findings over 10,104 rows. The four sampled clock pin rectangles and the two central SRAM `rd_out[0]` rectangles match the earlier checkpoint. Their sampled first-via wire stubs retain the local geometric clearance against the new PG and OBS. These checks cover local geometry. Router pin access, the continuous clock route and full PG graph signoff remain open.

Placement unit `oth-ubuntu-1216567-1795706135` exited 0 and stock DPL found zero wrong regions, row or site alignment errors, overlaps, edge-spacing or padding violations. The producer skipped pre-placement equivalence under `LEC_PREPLACE_DROPPED R-MINIMAL`. The RRL265 guarded hook retains the three earlier split lengths of 138.402, 123.606 and 121.770 µm.

## Exact evidence

- Source `ffbe77`, form `ee6c2255`. Final `3_place.odb` and stock-rendered `3_5_place_dp.odb` SHA-256 `755bda03ea4c304fe6251919a451579dd39b9b36aaa0a5cd5c3e8fd8237fe45a`.
- Stock layout SHA-256 `22017a859e328af528575afbe200b507e3922d83fd00ac1055aa00a9429b6f4d`, density SHA-256 `9e30eb00695cba9528b227897a17d53a767cba566dced980f4d90163f321e951`. Both sets of image bytes match the prior ff95 checkpoint. The new referenced ODB differs.
- E7 kit `/srv/opentallas-scratch2/claude/head-west/west_w10_pg_ck5_preparation_1126/kit_work_ffbe77/gen/hd_lep0N_w`. Stock images are under `run/layout_review/place`.
- E7 overlay `/srv/opentallas-scratch2/claude/head-west/west_w10_pg_ck5_preparation_1126/independent_visual_755bda/pg-pin-windows.png`, SHA-256 `0e46ebf2eaeed7643d16cd58cd615c8134e4d4ad1e9b4ef39a7f1c9af7fcdfd6`.
- Automated request `282bad25e8f166bc3357dbdc202d627f315c9ded4df3e9e033fd9bfba53facba`. This independent record leaves the automated verdict and active outputs untouched.
