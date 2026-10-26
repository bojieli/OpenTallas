# S81 p4l cross-die collectives with the switch crossing (TOKEN-XDIE-S81, 2026-10-18)

This is the multi-die part of the DeepSeek ROM (S81 p4l) token-pass release gate. It covers the TP all-gathers, the
all-reduce (out and expert combine), expert dispatch (the router-score all-gather), the argmax merge and the stage hop.
All of them run on the current p4l die RTL. Only the off-chip leg is modelled: PHY analog, cable and switch, at
377.6 ns a crossing.

## Vehicle

- **Bench:** `rtl/test/xdie_s81/tb_xdie_s81.sv`.
- **Dies:** N = 4, the production TP4 group.
- **Endpoints per die:** the 4 end-slice endpoints of the p4l plan (s_0S, s_7S, s_0N, s_7N). Each is
  `xdie_s81_ep` = `ot_s81sl_rstop` + `ot_s81sl_lep` / `_nh` + 2 x `dsfd_coll_lane_w/e` (LCR 1, kit GFMT 1, EPPIPE 2)
  + `ot_pdie_ucie` / `ot_pdie_serdes` (KP4 RS(544,514)) per plan lane.
- **RTL base:** `origin/claude/s81-die7-1018` 77083deda. The blob hashes are in `record.json` `vehicle.rtl_blobs`.
- **Fabric:** a one-tier multi-plane switch with static circuits: d.ES <-> (d+1).WS and d.EN <-> (d+2).WN. Every peer is
  one crossing.
- **Off-chip leg:** 453 cycles a crossing = the PMA model inside the PHY macros + a 445-cycle channel. That is 377.5 ns:
  PHY/FEC 100 + Tomahawk-Ultra 250 + 2 x 3 m twinax 27.6. The KP4 and link-layer RTL sit on top of it, which is
  conservative because the 100 ns budget already includes FEC.
- **Calendar:** static, from `tools/xdie_s81/gen_golden.py`.
  - Each port issues one beat a cycle (128 B of golden data per beat).
  - The AR all-gather phase is issued at its compiled cycle.
  - Deadlines are `max(start + 556 + ceil(1.345 k), previous deadline on the port + 2)`.
- **Checks:**
  - every beat is bit-exact and in order;
  - every beat lands by its deadline;
  - no fault, and 32 of 32 lanes are live.

## Final gate (`gate_g4`, dense calendar: 100 cycles between instances, 12,096 beats)

| run | lane tiles | verdict |
|---|---|---|
| min | as built, but CH_BOARD 700 and strap ch_b 1 | **PASS**: 0 late, 0 ACK timeouts, 0 replays |
| min_err | min + pad bit errors on every SerDes lane (1 per 7 cycles) | **PASS**, landing cycles identical (KP4 has fixed latency) |
| asbuilt | built tiles, plan strap ch_b 0 (CH_UCIE 100) | FAIL: 8,240 late (max +1,857), 256 timeouts, 42,208 replayed flits |
| board | built tiles, ch_b 1 (CH_BOARD 400) | FAIL: 1,212 late (max +264), 24 timeouts, 6,144 replayed flits |
| mutant swap / late / kp4d | min + the mutant | FAIL (all three). Witnesses: `gate_g4/witness_*.log` |

## Measured cycles (min, both repetitions; E = first issue to last land over all 12 streams)

| collective | payload | beats a peer | per token (AR DAG) | E_meas | DAG price |
|---|---|---|---|---|---|
| argmax_merge | 32 B | 1 | 1 | 553 (562 when queued behind a hop) | 375 |
| router_allgather (dispatch) | 1,536 B | 3 | 40 | 556 | 422 |
| a_allgather | 3,648 B | 8 | 40 | 563 | 434 |
| eng_rows_allgather | 6,336 B | 13 | 2 | 570 | 1,422 |
| idx_topk_merge | 16,384 B | 32 | 8 | 595 | 551 |
| cand_merge | 65,536 B | 128 | 1 | 723 | 1,002 |
| rows_allgather | 67,584 B | 132 | 40 | 729 | 1,033 |
| allreduce (out + combine) | 20,480 B | 40 + 40 | 80 | 1,212 (RS + AG; owner fold not included) | 827 |
| stage_hop | 40,976 B | 321 | 120 | 981 | 1,006 |

Scaling law: per crossing, `E = 553 + 1.337 x (beats - 1)`. For example, 132 beats gives 728 against 729 measured.
The TP collectives span one TP4 group, which is N, so no group-size scaling applies. The array size only changes the
stage-hop count.

## Composition (S81 part)

    T_token += sum_x n_x * max(0, E(x) - O(x)),  E = E_meas + 134 priced on-die cycles a crossing

- `O(x)` follows the composition's S81 rule on the token-path DAG: 0 on the critical path, `O = E` off it.
- The on-die cycles are the farthest slice <-> end slice legs, 67 an end. They lie outside this vehicle.
- `record.json` `token_compose` holds the 527 AR + MTP slot overrides.

Dry run of `tools/token_compose_xdie.py --xdie-records record.json` on main 64afe1eb2:

| mode | before | after | change | share measured on current RTL |
|---|---|---|---|---|
| AR | 1,365.7 tok/s | 1,243.0 tok/s | -8.98 % | 10.3 % (was 0) |
| MTP | 4,045.4 tok/s | 3,806.2 tok/s | -5.91 % | — |

Against the DAG basis, the token gains +86,986 cycles: +36.4k from transport and the switch, +50.6k from the priced
on-die legs.

## Findings

1. The built p4l link layer does not hold a static calendar over a switched crossing.
   - `ot_s81ph_link_ep`'s ACK-timeout basis is CH_UCIE 100 (plan strap) or CH_BOARD 400. Both are below the 553-cycle
     switched one-way latency.
   - Go-back-N timeouts replay the window and push later beats past their landings.
   - Fix: lane parameter CH_BOARD >= ~600 (700 measured) plus strap ch_b 1. No logic change is needed.
2. The S-tier ports pair a UCIe lane 0 with a SerDes lane 1. Both halves of a beat go to one peer, so a switched S
   port cannot use UCIe. This needs a coordinator decision.
3. CREDITS 512 is enough for these bursts (321 flits or fewer). A burst of about 830 flits or more would be
   credit-limited at the switched RTT.

## History (failed verdicts kept)

- `cal/`: isolated calendar, no deadlines. All three configurations are exact. The as-built stage hop takes 1,820
  cycles against 982.
- `gate_g1`, `gate_g2`: dense calendar. board and asbuilt FAIL.
- `gate_g3`: with CH_BOARD 700, 4 beats were 5 cycles late. The deadline model lacked port backlog, which
  `gen_golden.py` now includes. The kp4d mutant without pad errors PASSED, so it was invalid and has been replaced.

## Reproduce

Run from the repository root on a fleet host:

```
bash tools/xdie_s81/gate4.sh g4 a; bash tools/xdie_s81/gate4.sh g4 b
python3 tools/xdie_s81/record.py --golden out_g4/g/golden.json --run out_g4/min/run.log --name final \
  --out record.json --dag results/arch/token_path_20261009/ds_rom.json \
  --dag-mtp results/arch/token_path_20261009/ds_rom_mtp.json --compose
```

Cost: about 7 min and about 10 GB to build each configuration (24 GB with the C++ compile), and 4-20 min to run it.
