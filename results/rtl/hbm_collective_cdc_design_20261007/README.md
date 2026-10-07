# HBM collective protected CDC: architecture choice

## Update (v2): Codex's II1 refill (B′) on equal terms, with producer, reset and flight contracts

This is a design model; it changes no RTL, which is owned by Codex /hbm/collective. Run `python3 tools/hbm_collective_cdc_design.py` to regenerate `comparison_refill.json`.

The tool reads only committed repository files. Each of its 26 inputs is pinned by path and SHA-256 as committed on main at 9ead91a15 (where Codex committed the protected CDC, the II1 refill and their receipts) and carried by this branch. The tool checks every pin before running and fails closed on any mismatch (exit 1). The inputs include:

- `tools/hbm_collective_cdc_model.py` (`4828bd7e…`);
- `rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc.sv` (`a4e1bda9…`), `ot_hbm_collective_protected_cdc_refill.sv` (`1fe0c8eb…`) and both testbenches;
- `results/rtl/hbm_collective_cdc_20261007/{model,refill_model,diagnosis,admission_comparison}.json` and the pass records.

No snapshot copies are needed, because every file is identical on main.

Equal-terms comparison: 256 credits except A, Gray credit producer, and the same workload as v1.

| | A: 64 credits, II3 | B: three-bank rotation | **B′: Codex refill (recommended)** | C: 256-deep, II3 |
|---|---|---|---|---|
| Throughput | 1/3 | 1 | 1 | 1/3 |
| Per-token AR / MTP-step cost | +31.8 / +173.0 µs | +1.02 / +1.02 µs | +1.02 / +1.02 µs | +31.8 / +173.0 µs |
| Area added | 0 | +12,093 µm² | 0 state bits, about 60–100 µm² of logic | +290,238 µm² |
| Occupancy bound / CE repairs per gap-free stream | C ≤ D | 13 / 10 | 13 / 10 | D ≥ C |
| Evidence | model | model | **RTL measured (Codex, both records pass) + this model** | model |

**Recommendation: B′.** It passes every check that B passes, it adds no state, and its implementer owns it. B (rotation) is needed only if B′ cannot close SS after the address fix below. The v1 verdict, which recommended B, is kept unchanged as its own record (see the Historical section below).

### Contracts (each is an executable check with negatives)

All 34 checks pass. The negatives fail exactly as intended.

**Producer.** The receiving endpoint produces the RX credits. The native RTL has none today: the testbench stub preloads `eg_cred = 1<<RXAW`, and `rx_credit = rb_pop` is a core-clock pulse with no crossing.

- **Counters.** K is a Gray-coded retirement counter in the core domain. It advances +1 per receive-buffer pop (never per CDC pop), at most once per cycle. It is 9 bits wide, since W_c = ⌈log2(C+1)⌉. READY is a one-bit level.
- **Crossing.** Both cross into the PHY domain through 2-flop synchronisers. The PHY TX carries them to the partner.
- **Spend rule.** The partner spends `avail = (READY ? C : 0) + K_seen − sent` (mod 2^W_c).

The inequalities and their negatives:

| Inequality | Negative check that breaks it |
|---|---|
| 2^W_c > C | 8 bits deadlocks |
| 0 ≤ avail ≤ C on every sample | A binary multi-bit crossing over-grants |
| K_seen = pops after quiesce | A pulse synchroniser leaks credits |
| C ≥ RTT for full rate | — |

On the RTT, the labelled loop is 159 cycles. The conservative loop is 240 cycles:

| Leg | Cycles |
|---|---|
| PHY + cable forward | 77 |
| CDC | 6 |
| WSTG | 14 |
| Receive buffer | 2 |
| K register and sync | 4 |
| 113.8 ns return | 137 |

**256 credits leave a 16-cycle margin on the conservative loop.** Any added hop eats into it.

Do not deliver the initial C as a grant ramp. A ramp shares the counter with pops and leaves a permanent pending backlog under a continuous stream.

**Reset.**

- Either reset order is allowed. Each domain asserts reset asynchronously and releases on two local edges.
- READY rises only at max(t_core, t_phy) + (S+1) cycles of the slower domain.
- A cold POR is coordinated with the partner port: the partner's credits and the PHY's in-flight flits are discarded.

What is forbidden, and the negative that shows it:

| Forbidden | Result in the model |
|---|---|
| A partner that preloads credits at its own reset, as the current stub does | Write domain late → loss; read domain late → overflow |
| A partner that keeps stale credits across an endpoint reset | Over-grant or loss |
| A unilateral core-only reset | Out-of-order delivery |

The positive checks pass: write domain late, read domain late, and a coordinated mid-stream reset.

**Flight (TX).**

- **Gate.** The core may issue only while `issued − sync(rb_tx) < D_tx`. This counts the 14 WSTG stages and the synchroniser lag. It is exact under any pacer stall: a 500-cycle stall still leaves occupancy at 64.
- **Negative.** A gate on CDC occupancy alone overflows by the wire flight.
- **Full rate.** It needs D_tx ≥ 25. The check measures 0.989 at 25 and 0.79 at 17.
- **Switch-ingress credits.** The SWCRED = 256 switch-ingress credits sit on a loop of about 240 cycles, the same margin as the RX side.

**Frequency.**

- **Locked clocks** (same reference, independent phase): occupancy is at most 13.
- **Plesiochronous clocks** (PHY = core × (1+δ)): the partner must leave at least one idle per M flits, with M ≤ (Tw/Tr)/(1 − Tw/Tr) ≈ 1/δ. At 200 ppm, M ≤ 4999. Checked at δ = 1%: M = 50 passes; M = 200 and no idle both overflow.
- **Credit-starved partner with a slower drain:** the CDC settles at C − r·L_loop_min. That is a legal route only with a measured physical lower bound on the loop latency. It is not relied on; the short-loop negatives overflow.
- **Stress clock:** the 1024.6 ps read clock at 256 credits overflows.
- **Open question:** Ethernet rate matching must be shown to deliver the required idle rate to the endpoint. If it cannot, lock the clocks.

### B′ area and timing (structural estimate; Codex measures)

- **Area.** B′ adds 0 state bits and about 35 cells per FIFO: about 60–100 µm² over 16 FIFOs, under 0.05% of the 193,492 µm² of storage.
- **Timing risk as written.** The path is head-bank syndrome → normal → pop → refill → `refill ? rb_next : rb` address select → select fan-out into the 64:1 × 648 read mux → bank. That is about 27 levels, estimated at 650–800 ps SS against a 773 ps budget: **at risk**.
- **No-function-change fix.** Drive the read address from the registered `hp`: `addr = (hp==0) ? rb : rb_next`. The bank loads only on capture (hp==0) or refill (hp==2), so `encoded_d` is unchanged. The read mux then launches from flops at about 350 ps, and the late path becomes the load-enable fan-out at about 480–570 ps.
- **Activity.** The data activity on the head/mux path is three times that of II3. There is no measured power.

### Staged plan (v2)

- **S1 (Codex).** Apply the registered-`hp` address select in the refill RTL (no function change) and measure SS/FF and area.
- **S2.** Implement the producer contract in the native endpoint: K and READY transport, W_c = 9. Replace the stub's preloaded credits with READY-gated credits, and add the TX gate with D_tx = 64. Rerun the full collective gate.
- **S3.** Decide frequency lock vs idle insertion with the PHY owner. Apply the same refill to the II3 packet-SRAM queue. Recompose the ledger: replace +2 × 265 with the measured value.
- **Fallback.** If B′ misses SS after S1, use B (rotation). If clocks cannot be locked and idles are not guaranteed, use D ≥ C.

### Reproducibility

The check runs `git archive` of this branch into an empty temporary directory, with `HOME` pointed at an empty directory (so there is no `~/.claude` dependency), and reruns the tool there. The result:

- The rerun's `comparison_refill.json` is byte-identical to the committed file.
- Changing one byte of a pinned input makes the tool exit 1 with `INPUT_PIN_MISMATCH`.

The commands are in the commit message.

---

## Historical (v1, commit b49366616): recommendation B rotation, kept as recorded

`options.json` is the v1 output (branch `claude/hbm-collective-cdc-design-20261007`, commit b49366616, cherry-picked here as a70256191 with identical content). Its inputs are the 9ead91a15 files above.


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
