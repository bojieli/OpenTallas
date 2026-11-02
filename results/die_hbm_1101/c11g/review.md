# HBM c11G plan event: station siting + L730/L731 stations (DIE-HBM-57)

One plan event on top of Codex S11 (`codex-hbm-stationclock-1101/s11/die_plan.json`, sha256 2104b4d17cb3, train 8717480994c).
Result plan sha256 af2539e6d16e (file; = c11G e0638225f8b3 + su00 step H75). `c11g_patch.json.gz` = slot replacements + `replace_latency_lanes`;
`tools/mkpatch.py` checks that applying it to S11 rebuilds G exactly (canonical-json sha).

## Changes
| type (both instances where pv1 exists) | slot | change |
|---|---|---|
| q_spu0, q_spu0__physical_v1 | L730x5 | +1 station (5 -> 6), per-bit sited alpha 1.0 |
| q_su11, q_su11__physical_v1 | L730x7 | +1 station (7 -> 8), sited alpha 1.0, stage 5 nudged off u_sfu_Q1 (432 bits, max 48.3 um) |
| q_su11, q_su11__physical_v1 | L30x1, L31x1 | bit cells nudged off reuse contents u_cxdl_Q1_q/_s, u_hc_Q1 (L30x1 s4 762 bits; L31x1 s3 503 + s4 142; max 30 um) - root cause of su11 DPL-0033 since d44p |
| q_b002, q_b002__physical_v1 | L731x2 | +1 station (9 -> 10), west street then bottom street polyline, sited alpha 0.15 |
| q_su00, q_su00__physical_v1 | L730x1 | +1 station (7 -> 8, mk_d, die hops <=358.8 um), then per-bit siting alpha 0.75 (alpha 1.0 gave a 375.1 um die hop and was reverted by the composer); cbox 0 reuse hits |
| q_b010__physical_v1 | L168x1 | class-sweep per-bit siting |
| q_su31__physical_v1 | L35r0_1 | class-sweep per-bit siting |

Latency (gen.py latency --inplace; check.py clean): L730/L730m 42 -> 45 cycles, L731/L731m 17 -> 18 cycles.

## G0 / G0C vs S11
NEW: none. GONE: G0 4 ERROR + 4 WARN, G0C 8 ERROR (the L730 633 um and L731 623 um hops). Diffs are in `ledgers/`.
Worst die hop after the event: L730 362.9 um, L731 329.1 um; nothing over 364.5 um on either lane.

## Hop timing (REACH-M89, 833 ps)
Worst new station-to-station hop is 362.9 um (L730). Wire delay is 0.6315 ps/um nominal and 0.76 ps/um calibrated. Setup slack is about +80 ps nominal and +57 ps calibrated, so TT setup stays >= 0.

## G2 GRT probes (total overflow; 50-it rows are filled in as each run finishes)
| type | S11 0-it | c11 0-it | c11 50-it |
|---|---|---|---|
| q_spu0 / pv1 | 16,964 | 0 / 0 (F) | 0 / 0 (F) |
| q_b002 | 358,824 | 19,816 (F) | A-form pair 0; F running |
| q_su11 / pv1 | DPL-0033, no result | 651,232 (E, first-ever placed) | G running |
| q_b010 pv1 | 1,256,813 | 672,330 | running |
| q_su00 / pv1 | 1,548,089 | 39,331 / 39,331 (H75) | running |
| q_su31 pv1 | 11,068,380 | 10,088,098 | separate issue (open) |

Open: q_su31__physical_v1 ~10M overflow (separate issue). G0/G0C H75 vs c11G: NEW 0 ERROR; the only change is the su00 clk_t3 tap-sinks WARN, which drops from 9373 to 7710.
