# S81 SerDes t4 recovered-clock entry candidate

**SOURCE CANDIDATE, ROUTE HOLD.** Stock plan inputs generate a local M7 recovered-clock entry for `lk_WN3` and retain the pad clock, CDC contract and generated FCLK definitions. The candidate is for R11 plan SHA-256 `1f8fcdd9c4d7d3221a5c1dc2568ec7df87dd879d780445f4ff8d13401287c148`. The guarded two-field source row and exact generator checks are on E7 in `/srv/opentallas-scratch2/claude/codex-serdes-t4-rck-src-1126.0pcTFc/{row.json,source_geometry.json,source_check.log}`. I viewed the [source geometry](s81-serdes-t4-rck-local-entry.png) against the [exact placed checkpoint](20261126-s81-serdes-t4-place-gp-codex.md).

## Pre-CTS entry geometry

The current die terminal `io_pma_rck[0]` is at (1448.032, 1090.800) on M7. The same net reaches the RX macro’s `pma_rck` **input** at (332.712, 1082.064) on M5. The exact current and retained macro LEFs have the same digest, and the actual netlist and LEF agree on the input role. The reviewed placement shows 1,124.056 µm of direct terminal separation before PRE_CTS.

Move the BTerm to (332.768, 1090.800), a real M7 track in the same 10.800 µm inter-PMA slot. The 0.192 µm pin clears the actual VDDPHY M7 stripe by 0.128 µm. The immediately closer M7 track at 332.704 gives only 0.064 µm of pin-box clearance against the stock 0.072 µm spacing criterion. The proposed entry reduces the pre-CTS terminal separation to 8.792 µm. Stock PDN dimensions put the local M6 pair phase at 0 µm modulo 4.32 µm. M6 track y1082.080 passes that source check and intersects the real M5 pin rectangle. The candidate transition from M7 through M6 to M5 uses 0.056 µm of horizontal movement. Exact via enclosures, post-PDN rails and pin access remain checks for the revised physical input.

The TX south face has 544 `d` bits, `d_v` and `ck` on M5 entering the same cell-free slot between the macros. Their access and rail crossings remain an independent SerDes lane obligation. The line-facing coincident-contact review covers RX/TX data and TX clock on the other faces.

## Post-CTS timing

Stock PRE_CTS reassigns the RX macro clock to a matched entry. On the retained E7 sink geometry, its final driver-to-M5 leg is 188.473 µm. This is a placement projection. The direct 1,124.056 µm terminal span belongs to the earlier topology. The separate `fclk_out_ft0_o` remains a generated clock sourced by `clk_t36`. This candidate leaves its SDC intact, and the historical CTS-0114 overlap stays open.

The coordinate-only replay increased the matched tree from 17 to 31 stages. The row therefore also sets the existing stock `star.hop_um` from its default 92 µm to 200 µm. The exact placed-data replay retains 102 entries, 14 sub-hubs and 17 equal modeled stages, with 7 common feeder stages. The largest modeled segment was 207.25 µm versus 202.12 µm in the baseline. The modeled peak legs per 100 µm rises from 18 to 21, and the common feeder adds wire. Equal stage counts leave insertion and relative phase to TT/FF proof.

Keep this row review-only until the exact stock source plan passes PRE with real macro geometry. Its own revised placement needs visual review and phase/access evidence covering propagated recovered-clock insertion, branch skew, setup/hold, reset removal, source endpoint coverage and the M7/M6/M5 transition. The separate FCLK overlap must close before route. The original kit and event remain held.

## Sibling scope

All four center-fed sibling rows below use the same stock 92 µm default, 400 sink cap, 150 µm extent and 14 sub-hubs. Each has the same 1,124.056 µm pre-CTS geometric separation. Their pure source geometry establishes which mechanism applies. Their placed sink distributions and parent-side layers still determine their own proposal.

| Exact R11 type | RX/TX local Y origins (µm) | Clock BTerm Y (µm) | Die instance orientation | Applicability |
|---|---:|---:|---|---|
| `serdes__t13` | 925.560 / 1065.960 | 1063.800 | `lk_EN2` MY | The PMA pair sits 27 µm south of t4. Recompute vertical track and PHY stripe phase. |
| `serdes__t15__cla2127225` | 952.560 / 1092.960 | 1090.800 | `lk_WS0` MX | Local macro geometry matches t4. Recheck mirrored die landing and this type’s placed clock. |
| `serdes__t15__cla3d02796` | 952.560 / 1092.960 | 1090.800 | `lk_EN0` MY | Local macro geometry matches t4. Recheck the east-side mirrored landing and placed clock. |
| `serdes__t16` | 952.560 / 1092.960 | 1090.800 | `lk_WS1` MX and `lk_EN1` MY | One type serves both orientations. Check both physical interfaces and the exact placement clock. |

The six remaining R11 SerDes rows already align their clock X within 0.024 µm of their RX macro input. Keep their independent pin and timing receipts.
