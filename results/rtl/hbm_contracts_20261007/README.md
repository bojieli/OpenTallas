# HBM accelerator: four contracts implemented in RTL (2026-10-07)

Stream `hbm-contracts`, branch `claude/hbm-contracts-20261007`. Each contract below now has RTL, an exactness bench with
negative controls, and a physical screen launched through the closure loop. The bench record is
[`gate_all/record.json`](gate_all/record.json): `tools/hbm_contracts_gate.py --suite all`, Verilator 5.032, with
12 positives and 20 negatives, all behaving as required. Every source is pinned by sha256 in that record. The SM → SU
golden composition is in [`sm_su_composed/`](sm_su_composed/).

| # | contract | RTL | bench verdict | cycles / token | route (loop job) |
|---|---|---|---|---|---|
| 1 | SM → SU native result edge | `rtl/hbm_accel/contracts_20261007/ot_hbm_sm_su_result_edge.sv`, `ot_hbm_su_result_ingress.sv` | exact: 12/12 golden cases, both SM variants; 2 standalone positives; 6 negatives | 1,029 priced (measured ≤ that, see below) | `hbm_su_rin-*` |
| 2 | native credit producer (collective CDC) | `rtl/hbm_accel/contracts_20261007/ot_hbm_coll_credit_producer.sv` | 2 positives, 8 negatives | 0 per token; +3 cycles at link-up | `hbm_credit-*` |
| 3 | packet SRAM II=1 refill | `rtl/hbm_accel/collective_full_20261007/ot_hbm_collective_packet_fifo_refill.sv` (`ENABLE_SRAM=2` / `PACKET_SRAM=2`) | 4 positives, 3 negatives | removes the II=3 cap (+30.78 µs AR / +172 µs MTP in the design ledger) | `hbm_pkt_ii1-*` |
| 4 | clock lock | `rtl/hbm_accel/contracts_20261007/ot_hbm_coll_idle_insert.sv` | 4 positives (±200 ppm, at the bound, 1 %), 4 negatives | 0 for bursts ≤ 1,024 flits; worst case 0.098 % of TX slots | `hbm_idle-*` |

## 1. SM → SU native result edge (contract 8c8bb2af2)

- **Path.** The SM face is one-way: `{fault, rv, rrow[11:0], rdata[255:0]}`, 270 b, with no ready. It passes through:
  - an SM pin station;
  - `NST` relay stations, each made of five `ot_hbm_result_relay_slice` 64-b slices;
  - an SU pin station;
  - `ot_hbm_su_result_ingress`.
- **Flow control** is a credit reservation inside the ingress:
  - The SU command path may start an SM op only after the lane accepts `op_rows` (`op_v && op_r`).
  - The accepted rows are deducted from the 64 free slots, and each drained row returns one slot.
  - No ready and no credit return crosses the die, so the lane cannot overflow at any path latency.
- **Release is ordered by protocol.**
  - Rows become visible only after `arrived == op_rows`, and `op_done` pulses once per op.
  - Each row index must be below `op_rows` and is accepted only once, enforced with a 64-b map.
  - These are sticky faults: SM fault, a row with no reservation, a repeated row, a row out of range, and `op_rows` of 0 or greater than 64.
- **Storage** is one `ot_sram_1r1w_64x512_m1_r2c2` per SM lane (268 b used). Its 64 slots cover the 43 rows per SM per op on the DS AR walk. The read side uses the same II=1 refill head as contract 3.
- **Measured (standalone bench, 400 ops, NST = 49 = r23 worst path `result_sm8`).**
  - One-way latency is **51 cycles**, the r23 floor stated in the contract.
  - `op_done` comes 1 cycle after the last row reaches the ingress.
  - The first row of the completed op is visible on that same edge, because the head is prefetched.
  - Per barrier this gives SU pin station +1 and ingress +1. That is within the priced +1 station / +2 ingress, so **1,029 cycles/token** stays the published figure.
- **Golden.** `tools/hbm_sm_su_composed_gate.py synth --simulator verilator --cols 1 2` runs W13's SM vectors with the SM result face routed through the edge. The rows are reserved before `start`, and the consumer applies random back-pressure.
  - **12/12 cases are bit-exact against `hdc_golden_v41`** for the original `ot_gpu_sm_v` and for the 1.2 GHz `ot_hbm_accel_sm_v`.
  - A payload mutant inside the ingress head is detected in 6/6 cases.
  - Recorded "done" cycles include the ingress drain, so they are not SM start → done.
- **Negatives.** Each of these fails as required:
  - an op started without a reservation;
  - a repeated row;
  - the SM fault pin;
  - a release-before-count mutant;
  - a credit-not-returned mutant.
- **Area.** Each lane has one 64x512 macro (171.3 × 77.8 µm) plus about 690 flops. For 32 lanes the macros alone are about 0.43 mm². The contract estimated 0.14 mm² of raw DFF.
- **Still open.**
  - The die stations are the r22 relay64 primitive (Codex's screen: NS closes, EW does not).
  - Joining the ingress to `ot_hbm_accel_su_parent_exec`'s operand path and the cmdproc reservation is the SU owner's integration.

## 2. Native credit producer for the collective CDC (contract 2ae0d7d33)

- **Producer** (`ot_hbm_coll_credit_producer`, RX endpoint, core domain):
  - K is a 9-bit Gray retirement counter, +1 per receive-buffer pop.
  - READY is one level. It rises **exactly SYNC+1 = 3 core edges after the later of the two releases**, and the bench checks that on all 3 releases.
- **PHY side and partner.**
  - `ot_hbm_coll_credit_phy_tx` holds the PHY-side synchronisers.
  - `ot_hbm_coll_credit_consumer` is the partner. It computes `avail = (READY ? 256 : 0) + K - sent (mod 512)`, and C is added on READY, never counted.
- **TX flight gate** (`ot_hbm_coll_tx_flight_gate`):
  - It issues only while `issued - sync(TX CDC pops) < D_tx`.
  - The popped count and `allow` are registered, so there is no combinational path from the synchroniser to the
    issue decision. The first physical screen had one (SS −127.6 ps, `allow` and `can_send` driven combinationally
    to the block pins). Both are now registered and conservative: the bound is never exceeded, and inflight ≤ D_tx stays exact.
  - The elaboration check is `D_tx >= WSTG + 2*SYNC + H + 7 = 27`: the design model's 25 plus those two registers.
  - Measured in the bench: full rate down to D_tx = 22; D_tx = 21 loses rate (82–91 %, negative `NEG_credit_dtx21_rate`).
    The default D_tx = 64 is the TX CDC depth.
- **Consumer output.** `can_send` / `avail` are registered from the already-registered K and the send count that
  includes the current send. They never exceed the true availability. The credit loop gains one edge (242 + 1 of 256).
- **Assertions** (simulation):
  - CREDIT_WIDTH;
  - CREDIT_LOSS (a pop before READY);
  - CREDIT_READY_EARLY;
  - CREDIT_OVERGRANT;
  - CREDIT_OVERSEND;
  - CREDIT_K_BACKWARDS;
  - CREDIT_STALE (the partner keeps credits across the far end's reset);
  - the D_tx bound;
  - TX_FLIGHT.
- **Bench** (`tb_coll_credit_producer`). The path runs partner → forward 77 cycles → the committed protected CDC (II=1 refill) → RB(256) → random drain → producer → PHY synchronisers → return 137 cycles → partner.
  - The synchronisers model metastability: a bit that changed within 20 ps of the edge resolves to old or new at random. The positives saw 900–1,900 such samples per synchroniser.
  - A continuous drain sustains ≥ 98 % rate at C = 256 over the 240-cycle conservative loop.
  - Conservation holds after quiesce.
  - Coordinated reset works with either domain released 400 cycles late, and with simultaneous release.
  - The TX gate shows no CDC overflow at D_tx = 64 under long PHY stalls, and full rate at D_tx = 27.
- **Negatives.** Each fails as required:

  | negative | failure |
  |---|---|
  | partner preloaded at its own reset (the legacy stub) | CREDIT_LOSS |
  | binary counter on both sides | K_BACKWARDS |
  | READY without the PHY release | READY_EARLY |
  | CW = 8 | WIDTH |
  | C = 192 | CREDIT_RATE |
  | TX gate on CDC occupancy only | TX_FLIGHT_OVERFLOW |
  | D_tx = 26 | refused at elaboration |
  | D_tx = 21 with the bound check removed | TX_RATE |

- **Cost.** 0 cycles per token. About 140 flops for producer, synchronisers, consumer, gate and reset synchronisers (Yosys count of `hfd_coll_credit_prod`).
- **Integration.** The endpoint's `rx_credit` pulse and the bench preload are replaced by K/READY carried in the PHY TX control field. That carriage is a vendor-PHY field and remains a labelled assumption.

## 3. Packet SRAM II=1 refill

- **Mechanism.** The head is two slots with no new data register: R is the macro's read latch, and H is the captured encoded word.
  - A pop moves R to H.
  - The next read refills R on the same edge.
- **Measured.** One flit per edge: 64 flits in 64 edges, and 256 in 256. The II=3 queue takes 190 edges for 64.
- **Registered-address fix.** It is **not needed** here: the SRAM address is already the registered `c_rp`, and `pop` reaches only `r_ce_in`, the head load enable and the control next-state.
- **Unchanged from II=3:** ECC, seal, overflow and count semantics. The legacy II=3 bench passes against the same storage.
- **Finding.** The committed II=3 source (`ot_hbm_collective_packet_fifo.sv`) **does not parse in the ORFS Yosys 0.68 frontend**, because of the wildcard `import` inside a generate block. It has never been routable as written. The refill is written with package-scoped calls and synthesises with 3 macros.
- **Use.** `PACKET_SRAM=2` in `ot_hbm_collective_full_candidate` / `ot_hbm_collective_native_link_candidate` selects the refill. The default is unchanged.

## 4. Clock lock: mesochronous on the die, plesiochronous between dies

The repo's clock specification:

- **On the die, the core and PHY-side clocks share a reference.** In `tools/hbm_accel_die_fp.py` `SDC_R15`, `clk_stream` and `clk_link` are both outputs of the die PLL `hb_coll` (`pll_stream`, `pll_link`, 0.833 ns). `results/uarch/hbm_collective_clock_entry_20261007/model.json` names the domains `stream_1p2` and `link_1p2_independent_phase`. The endpoint CDC (pclk ↔ core) is therefore **mesochronous**: equal rate, independent phase. That is the locked case, where the II=1 drain is ≥ arrival.
- **Between dies the clocks are recovered.** Inter-die collective traffic crosses an IEEE 802.3 PHY/FEC and a Tomahawk-Ultra-class switch over 3 m twinax (`tools/dshbm_1m_coll.py` budget; `SDC_R15`: "L* … plesiochronous at the link macro"; `docs/ARCH_V41_RACK.md`: every device runs its own reference at ±100 ppm). The link is therefore **plesiochronous**, with δ ≤ 200 ppm end to end.
- **Required contract.**
  - Every transmitter leaves at least one idle slot after every M consecutive flits, with M ≤ (1−δ)/δ = 4,999 at 200 ppm. The receiver's elastic buffer writes flits only.
  - `ot_hbm_coll_idle_insert` uses M = 1,024: a 4.9× margin, at a worst-case cost of 0.098 % of TX slots.
  - A collective stream of PF384 per port has gaps between collectives, so no idle is forced in practice.
  - Sustained arrivals at the endpoint RB are additionally bounded by the credit loop of contract 2, which returns credits at the RB pop rate.
  - PCS rate matching inside the vendor PHY (deleting those idles) remains a labelled vendor obligation.
- **Bench** (`tb_coll_idle_insert`). The TX runs δ faster or slower than the RX, and the elastic buffer is the committed protected CDC (64 entries).

  | case | flits | M | δ | result |
  |---|---|---|---|---|
  | positive | 1.5 M | 1,024 | +200 ppm | occupancy ≤ 5 |
  | positive | 1.5 M | 1,024 | −200 ppm | pass |
  | positive, at the bound | 3 M | 4,999 | 200 ppm | occupancy ≤ 10 |
  | positive | 300 k | 50 | 1 % | pass |
  | negative: no idles | — | — | 200 ppm | overflow after 286,046 flits |
  | negative: above 1/δ | — | 200 | 1 % | overflow |
  | negative: above the bound | — | 6,000 | 200 ppm | refused at elaboration |
  | negative: rule-removal mutant | — | — | — | spacing assertion fires |

## Scope and reproduction

```
python3 tools/hbm_contracts_gate.py --suite all --out DIR            # all four contracts, Verilator
python3 tools/hbm_sm_su_composed_gate.py synth --simulator verilator --cols 1 2 --out R.json
python3 tools/hbm_sm_su_composed_gate.py synth --simulator verilator --cols 2 --out N.json --mutant payload
python3 tools/hbm_contracts_physical.py --block {pkt_ii1,su_rin,credit,idle} --out DIR
```

- **Physical routes.**
  - The routes are block screens: SS ≥ +15 / FF ≥ +15 / DRC 0 at 833.333 ps with 60/25 ps uncertainty.
  - IO is an envelope of 20 % each way, because no budget sheet exists for these new masters. Die-context IO binding is a separate gate.
  - The credit block's screen ties the PHY and partner clocks to `clk`, so every synchroniser path is timed as a single-cycle path. That is stricter than the real asynchronous crossing.
