# HBM collective protected CDC: architecture choice

This is a design model and recommendation. It changes no RTL; the RTL is owned by Codex /hbm/collective. The data is in `options.json`, which `python3 tools/hbm_collective_cdc_design.py` regenerates. The tool reads the read-only snapshot `cdc_snapshot_1130`, whose three pins match, together with the committed sources listed in `options.json.sources`.

## Problem

| Item | Value | Source |
|---|---|---|
| PHY write clock / core read clock | 833.333 ps / 833.333 ps, independent phase | clock-entry model, protected-CDC model |
| PHY edge rate | 1 flit/edge (pacer 720 > 545 bits) | `ot_hbm_collective_full_candidate.sv` |
| Switch-egress credits | 256, returned at receive-buffer pop (downstream of the CDC) | `rx_credit = rb_pop` |
| RX CDC write back-pressure | none (`ph_rx_v` must be accepted) | native candidate |
| Protected CDC | 545 b, 64 slots, drain II=3 (capture, validate, present on one W2 head bank), +2 read cycles | snapshot `ot_hbm_collective_protected_cdc.sv` |
| Credit loop RTT | 159 cycles (113.8 ns labelled loop + 23 local) | `collectives.json` budget |
| Per-token RX streaming (matched hub) | 18,470 cycles AR (P1), 103,196 cycles MTP step (P6), 305 crossings | `collectives.json` × `program.json` |

The simulator reproduces the problem: the II=3 candidate with 256 credits overflows at 65 under sustained traffic (`NEG_candidate_II3_D64_C256`).

## Options

The three options and the original CDC, side by side:

| | A: credit bound | **B: rotated II=1 (recommended)** | C: deep FIFO | Original (unprotected) |
|---|---|---|---|---|
| Safe inequality | **C_adv ≤ D** (64), with no timing assumption | Tw ≥ II·Tr and occ ≤ ⌈((S+2+H+K)Tr+(S+2)Tw+2t_m)/Tw⌉+1 ≤ D−1 → 13 at K=0; K ≤ 50 → ≤ 10 CE repairs per gap-free stream | **D ≥ C_adv** (256); a drain-only argument still needs about 184 | Tw ≥ Tr |
| Credits | 64 (switch-side parameter) | 256, unchanged | 256 | 256 |
| Sustained throughput | 1/3 flit/edge | 1 | 1/3 | 1 |
| Throughput cost per token | +36,940 cyc = **+30.78 µs AR (+6.48 %)**, +206,392 cyc = **+172.0 µs MTP step (+16.4 %)** | 0 | same as A | — |
| Latency cost | +2 cycles per CDC traversal = +1,220 cyc = +1.02 µs (0.21 % AR) | same as A | same as A | 0 |
| Area | 0 | **+12,093 µm²** (16 FIFOs × 2,592 b DFF) | +290,238 µm² of flops plus a 256:1 × 648 mux; no dual-clock SRAM macro exists in the asap7 set | base 193,492 µm² of flops (all options) |
| Reset entry | Insensitive to release order (C ≤ D) | Credits may be advertised only after both domains release + (S+1) | Insensitive | — |
| CE / stall robustness | Unbounded stalls are safe | A bounded budget (10 per stream), then sticky fault, fail-closed | Unbounded stalls are safe | — |

The A bound is tight. Simulation passes C = 64 with the read domain held in reset (occupancy 64) and overflows at C = 65. Option C fixes overflow only: at II=3, no finite depth absorbs 1 flit/edge sustained, because occupancy grows by 2/3 flit per edge.

## Recommendation: B with three protected head banks in rotation

- **Head banks.** Keep three W2 protected head banks, unchanged, and select one by the commit index mod 3. A capture pointer, itself a W2 protected bank, runs at most 3 slots ahead of the protected commit pointer. Only the commit pointer is Gray-synchronised, so freed space and credit stay exact. Capture, validate and present overlap, which gives II=1 with the same per-flit checks, the same fail-closed faults and the same first-flit latency as the candidate.
- **Credits.** Native credits stay at 256. The RX CDC needs no new credit, because receive-buffer depth (256) ≥ C, so its drain is never back-pressured.
- **TX.** Add a local gate on the TX side: issue only while `issued − sync(rb_tx) < D_tx`, counting the WSTG flight. This runs at full rate because D_tx = 64 ≥ 25.

All 17 simulation checks pass: 10 positive checks over randomized and adversarial grids of 16 seeds, and 7 negative checks that overflow as they must.

| Check | Result |
|---|---|
| B under sustained, burst and random traffic and consumer stalls | Occupancy ≤ 5 against a bound of 13; 0.998 flit/edge |
| B with 10 CE repairs | Occupancy 55 against a bound of 63 |
| Overflow negatives (all overflow as expected) | A CE storm beyond the budget; credits advertised before read release; a write clock 1 % fast on a long stream; the 1024.6 ps stress read clock at 256 credits |
| Stress clock at 64 credits | Passes, i.e. A acts as a fallback |
| TX: B with the local gate | Passes |
| TX: II=3 without the gate | Overflows |

## Residual risks

1. **B requires frequency lock between PHY and core**, or a PHY rate-matcher that delivers at most 1 flit per core cycle. With a plesiochronous PHY clock, a long stream overflows (a negative check shows this). The fallback is B with D ≥ C, i.e. B combined with C: +0.29 mm², with no timing assumption.
2. **CE budget.** More than 10 correctable-error repairs inside one gap-free stream overflow. This is detected as a sticky fault; it is not silent corruption.
3. **Timing at full activity.** The 64:1 × 648 b capture mux now launches every cycle. SS/FF timing of the mem → bank path is still unqualified.
4. **Ledger under-pricing.** The unified ledger charges the II=3 packet-SRAM queue +2 cycles × 265. At II=3, the receive drain caps a port at 1/3 of line rate, i.e. **+30.78 µs AR and +172 µs MTP per token**. The packet SRAM needs the same rotation, or it moves the bound downstream.
5. **Reset ordering.** Credits must be advertised only after both domains are released (`endpoint_rearm_ready`). The switch stub's initial credit load has to honour this.

## Staged plan (owner: Codex /hbm/collective unless handed over)

- **S0 (now).** Any gate that uses the II=3 candidate must advertise ≤ 64 credits per port (option A) and charge the throughput cost above. Correct the +2 × 265 ledger line for the packet SRAM.
- **S1.** Add `ROT=3` to `ot_hbm_collective_protected_cdc` (default `ENABLE=0`), with a protected capture pointer and rotation code. Extend `tb_protected_cdc` with:
  - sustained 1 flit/edge at 833.333/833.333 ps;
  - a phase sweep;
  - CE injection within the budget;
  - negatives: `ROT=1` at line rate, and early credit advertisement.
- **S2.** In the native candidate, add the TX local gate and advertise RX credits after `endpoint_rearm_ready`. Rerun the full collective gate on the actual clocks.
- **S3.** Apply the same rotation to the packet-SRAM queues, then measure and recompose the per-token cost. The expectation is +2 cycles per traversal, i.e. +1.02 µs AR.
- **S4.** Take S1 and S2 to SS/FF and record the area, launching in parallel with exactness. In parallel, decide whether the clocks are frequency-locked; if they are not, use the B+C fallback.
