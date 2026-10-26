# S81 241-stage MU calendar: causal six-position MTP pipeline (overlap424 fix), STEWARD-TOK 10-21

Grade: **MODEL**. This is exact integer calendar arithmetic on composed node cycles. The RTL calendar programme has not been emitted yet.

## Why
The 6f8bbf5c4 MTP law serialised each LINK5 stage circuit using one position's message lengths. The checker then stretched every message to 6 x H_MSG. As a result, x L0 [18136,22048) and partial L0 [21624,25536) of the SAME user overlapped by 424 cycles, on 200 of 240 circuits. The old checker skipped same-user overlap.

Codex's fix (85ce942d9, ii704_receipt.json) used six fully barriered positions with no pipelining. It is correct but very pessimistic: 1 user x 656.8 tok/s.

## Law (`--release241`, `REL241.mtp_law = 'pipeline'`, tools/s81_dv/dv_mu_calendar_phys.py `timeline_positions`)
- **Stages run position-major.** A stage runs all its items for position p, then moves to p+1 (the 6 W - 5 scan law). Positions 1 to 5 skip the shared idx.score scan.
- **Every message is real.** Each position's x, partial, combined and DENSE2 message is a real H_MSG on the one LINK5 circuit. Messages are serialised in send order across all positions.
- **Arrivals propagate.** Arrival = serialised send + HOP. The receiving item for that position waits for it.
- **Heads run per position,** followed by the draft tail.
- **Holds.** The stage copy is held from first start (less the 447 land lead) to last end, for one job context.
- **Same-user check.** The checker includes same-user windows (Codex b798551bb).
- **Example circuit.** R001->R002 now carries 12 serialised messages and 0 overlaps.

The step period stays at max(6f law 1,684,167, causal step end 1,485,794 + AR tail 25,283). The per-user rate is therefore unchanged. The causal step alone would give about 3,303 tok/s per user, but that is not adopted.

## Result (AR unchanged, byte-identical apart from the recorded law key)
| attention | AR | MTP (step hold, uniform shifts) | old 6f MTP |
|---|---|---|---|
| G16 | 50 x 982.8 = 49,140 | **6 x 3,006.2 = 18,037** | 10 x 3,006.2 = 30,062 |
| G8 | 50 x 972.6 = 48,630 | **6 x 2,991.8 = 17,951** | 10 x 2,991.8 = 29,918 |
| G4 (release) | 50 x 952.8 = 47,642 | **6 x 2,963.4 = 17,780** | 10 x 2,963.4 = 29,634 |

All rows pass the checker: 0 collisions, same-user included. The N+1 control faults, as it must. The injected-shift control faults, as it must.

**Binding resource:** the pipeline wave. The copy-B DENSE2-B stages are the per-position bottleneck: R013 (L2) 44.5k, R085 (L14) 47.8k and R121 (L20) 48.1k cycles a position, against about 6k on the other stages. Each downstream stage is therefore held for about 5 x 48k plus its own work. R091 holds 258,843 cycles a user, so 1,684,168 / 258,843 = 6 users.

**Sensitivity, G4pos** (`--mtp-hold position --mtp-shift-search`): one job a position, with the copy free between positions. This still gives 6 users. A randomized search over 300 orders also topped out at 6.

**Structural lever (owner):** halve the per-position work of the three copy-B index/Engram stages, for example by a further dense split. That would roughly halve the wave, giving about 11 MTP users.

`run_pipeline241.sh` holds the exact commands. `CHECK=1` reproduces every file as SAME.
