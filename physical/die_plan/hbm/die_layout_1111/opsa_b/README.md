# opsa_group0 re-floor in q_b113 / q_b113__physical_v1, form B (DIE-LAYOUT-HBM 11-11), DO_NOT_COUNT

- Base: base0 = d49a e9ae418c06ca + d6d (CPL-HBM-B1 16eaee4a), sha fc8d47cd26a1.
- Result plan: e4ae695c7698.
- Delta: opsaB_delta_on_base0.json.gz (ladder_delta.py format, from die_layout_1111/io_reform/). It touches only partition_types q_b113 and q_b113__physical_v1.

## Why form B, not A
- Form A (+74.52 um up) closes the band above g0 to 3.24 um.
- In q_b113__physical_v1 (NE), the L5076x3 crossing (653 b, N face -> W face) runs in that band. It would need a detour around g0 with +2 stations, which is +2 cycles.
- Form B keeps a 41.04-um band, so no station count changes.

## The change, in type frame, both types
- g0 goes from 760.32x233.28 at (1080, 1261.44) to 895.32x270.00 at (945.0, 1261.44): +135 um left and +36.72 um up, +36.3% area.
- The MX orient is kept, and the bottom edge toward g1 stays put.
- Pins file: `cores/ot_hgi_sfu_opsa_group0__895.32x270__d51opsaB.json`. It is PROVISIONAL; HBM-CORES-B owns the real view.
  - Every pin gets x + 135, so physical x is kept.
  - Core-frame N-face pins (toward g1) get y + 36.72.

## Station moves (counts unchanged, legs <= 405 um asserted)
| type | slot | stations | moves | worst leg (um) |
|---|---|---|---|---|
| q_b113 | L1271x7 (512 b) | 17 | S11-S15 up into the band at y 1551.96 | 403 |
| q_b113 | L8350x3 (1615 b) | 7 | S3-S6 go around the W end of g0 | 363 |
| q_b113__physical_v1 | L5076x3 (653 b) | 6 | stations from y 1528 to y 1551.96 | 347 |
| q_b113__physical_v1 | L5096x8 (70 b) | 9 | S5 below g0, S6-S8 into the band | 387 |
| q_b113__physical_v1 | L8350mx3 (1615 b) | 7 | S3-S6 go around the W end of g0 | 363 |

- L1247x1 (1 b) stays at y 1570.86, above g0.
- The L1224_i, L1254_i and L3003_o face windows are unchanged.
  - L1224_i: its legs cross g0 on M6.
  - L1254_i and L3003_o: their legs stay W of g0.
- The L8350x3 move was not in the brief ("left ft L8350x3 untouched"). The +135-um left extension forces it.

## Gates
- **G0** (main check.py): 551 -> 551, 0 new, 0 lost. WARN 1820 -> 1822.
- **Strict bind** (two-pass, epyc8 via ot-run, private copy): BIND_OK. 92 partitions, 420 crossings, n_errors 0, stale 0, uncovered 0, pad_flops 945867. These match io19. The receipt is bind_opsaB.receipt.
- **route_supply** q_b113 / pv1: p99 6.254 / 5.028, unchanged. The worst bins are elsewhere: face V / street V.
- **Seam hops:** unchanged. Only internal slot stations moved.

## Rebase note
- d50a (d6d + seam respace) may re-site q_b113 slot stations, for example L1269.
- opsa_b.py re-applies on any base. It asserts the g0 origin and outline, and stops on any station it cannot place.
