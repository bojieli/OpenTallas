# MTP die and array plan (stream mtp-die, 2026-10-08)

This plan covers the MTP step for the DS-V4.1 ROM S81 array and the HBM accelerator. It gives top-down budgets, the die and array homes of every MTP function, the generator variants that place them, and the die-level runs queued against them.

- Plan record: `plan.json`, written by `python3 tools/mtp_die_plan.py`.
- Generator check outputs: `checks/`.
- Chain scripts: `jobs/`.

Nothing here is a new measurement. Every row is labelled measured, derived, budget or model-only.

## 1. Budget sheet

The block streams (mtp-rom, mtp-hbm) route against these budgets. Source: `plan.json` → `budget`.

DS ROM today: HALF_PHL, 4,351.6 tok/s at τ 4.159.

| Term | µs | Class |
|---|---|---|
| Step | 955.74 | |
| Verify (AR 690.75 + 5 × II) | 829.57 | derived |
| II | 27.76 | derived |
| Draft | 122.95 | 3 blocks 83.99 + FEC delta 3.58 + 5 head steps 35.22 + 195-cycle adder |
| Seed / commit | 3.217 | |

Block budgets for the DS ROM:
- **WFC:** handoff ≤ 49 cycles and hop delta ≤ 13 cycles (measured).
- **WFC shims:** ≤ 14 cycles per stage per position.
- **Accept:** ≤ 3 + 2 cycles.
- **acc_n / squash:** a 16-bit field on the existing token return.
- **Chain FSM:** ≤ 4 cycles per head step.
- **Draft row link:** 512 b/cycle, full KP4 hop of 1,008 cycles.
- **UCIe pair:** ≤ 10 ns + 2 × 8 cycles.
- **Markov head:** ≤ 54.6 ns per draft row. This term is model-only.

HBM: 3,700.3 tok/s upper bound. Step 1,123.97 µs = verify 1,075.1 + draft 45.28 + seed 3.567.
- The hfd_mtp ↔ cmdproc command round trip is ≤ 16 cycles, and all MTP control together stays ≤ 1 % of the step.
- Argmax die merge: 16 cycles. 96-die select: 24 cycles, plus 2 × 10 relay stages to hfd_coll.
- Union: +1 cycle per flush.
- Top-k: +1 cycle per select.

## 2. DS ROM array

### Draft-die count: 64 vs 52

DP1-EP5 needs 64 dedicated dies (4 primary + 60 expert replicas). Its "12 baseline draft dies" are the TP4 × 3 blocks of the old timing model. Meanwhile the rack's 12 head dies still carry the whole drafter (15,131 DSpark pairs, 1,261 per die) as head content, and DP1-EP5 never reads it.

### Proposal P2 (package-pair fan-out)

| Item | Placement |
|---|---|
| DP1 primary | Head dies h0..h3: one head TP4 group. Head die content drops from 1,472 to 511 pairs: globals 211 + primary 282 + Markov 18. |
| Expert replicas | 5 row packages × 4 ranks × 2 dies = **40 draft dies**. Die A holds mtp.0 + half of mtp.2; die B holds mtp.1 + the other half of mtp.2. That is 1,680 of 1,792 pairs (layer1 recipe). |
| Primary links | 5 SerDes per primary head die (one per row package), down from 15. |
| B-die traffic | Reaches die A over in-package UCIe, cut-through. |
| Expert sum | Kept in id order on die A, so it stays exact. |

Rejected topologies:
- The 15-link star costs 9.28 mm² per die and needs 64 dies.
- The board tree adds +2 full-FEC hops per block (+5.0 µs per step) and still needs 64 dies.

Effect of P2:
- Array: 428 dies instead of 440, −12 dies (−10,071 mm²).
- Draft path: +0.2 µs per step (budget), −0.02 % MTP.
- s81-dies owns the array v2 composition.

### Homes

- **Sequencer:** `ot_dsrom_mtp_seq` (dsfd_mtp_seq, 0.15 mm²). It sits on head die h0, in the spine centre stack between capture and collective. Generator option `--mtp-seq`.
- **Accept:** inside the sequencer.
- **Markov head:** on the head dies. The `markov_head.head` rows sit beside the lm-head rows, with a separate 32-term accumulator and the golden add order. The embed table is replicated on every head die. This has **no RTL** (gap MTP-G1).
- **WFC:** a bound `dsfd_wfc` slab on EVERY layer-class die (`--wfc-hard`). The m221pq layer1 die carries no WFC today, because the soft 0.456 mm² reservation was built only on the 4-stack scan die.
  - Real need: 0.114 mm² (src 78,190.7 + stg 35,941.7 µm² routed).
  - Slab: 1,728 × 231.12 µm = 0.399 mm².
  - The capture slab grows to 129.6 µm so its face carries the new endpoints.
- **Main hidden (L37–39):** carried as a trailing payload on the stage hops: 24,576 B per position, 384 cycles per hop of link occupancy (1.15 %), 0 exposed latency.
- **Window rows:** 205,824 B per user, in the head-die HBM.

## 3. HBM die

- **r25m** = r25 + hfd_mtp + loader memory wiring. The variant is `--ds-var r25m`.
- **hfd_mtp:** 466.56 × 200.88 µm (0.094 mm²), in the free bottom of the spine column below the loader. Its cells total 41,824 µm², from the closed control routes.
- **ECO pins:** t_mtp / f_mtp on the S face of the closed `hfd_cmdproc_s`.
- **Loader memory side:** 4 stacks × (request 904 b + response 624 b) as forwarded chains to every stream service, on a new "lm" lane. This adds 88 stations (0.307 mm²); the worst path is 57 stages. In r25 these ports had no die net: they were tied to a cfg shift chain (RQ-ING-4).
- **Die outline:** unchanged.
  - r25 / r25m: 30.59 × 24.62 mm.
  - r25s / r25sm (attention half split + MTP + loader): 30.59 × 25.73 mm, 787.15 mm².
  - Headroom on r25s / r25sm: 0.27 mm in height, 2.41 mm in width, 70.9 mm² in area.
- **Full FEC on the 23 draft collectives:** +3.64 µs per step, taking 3,700.3 to 3,688.4 tok/s. This is a derived price, not a measurement.

## 4. Die-level evidence (queued, memory-gated)

| Host | Run |
|---|---|
| EPYC3 | `jobs/s81_mtp_chain.sh l1wfc` |
| EPYC3 | `jobs/s81_mtp_chain.sh headmtp` |
| EPYC1 | `jobs/hbm_r25m_chain.sh` |

Each run goes: real case → CTS-validated clock plan → die STA kit → full-die GRT + GRT-parasitic STA (TT / FF / SS) → rebudget link dump.

The MTP masters are interim placeholders until mtp-rom and mtp-hbm close the blocks.
