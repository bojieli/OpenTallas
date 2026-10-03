# HBM comparator owner/ACK bridge: dependency graph and field sizing

Main `7baca4be1`, read-only. The input gap review was written at `b1397a050`. None of the cited RTL or tools changed between the two commits. Full data is in `hbm_bridge_dependency_and_fields.json`, produced by `gen_bridge_dep_fields.py`.

## 1. Dependency graph (strict edges only; benefit edges are in the JSON)

F0 is the field-width specification in section 3 of this note. It is a modelling step, not RTL, and it must come first: every successor port width depends on it.

| layer | items (can run in parallel within a layer) |
|---|---|
| 0 | F0, W1 |
| 1 | W2, W4, W6 (need F0); W12 (needs the W1 provider successor) |
| 2 | W3 (W1, W2); W5 (W2, W4, W6); W10 (W2, W6) |
| 3 | W7 (W2, W4, W5, W6); W8 (W2, W3, W5, W6); W9 (W5, W6); W11 (W2, W10) |
| 4 | W13 (W7, W10, W11) |

- **Critical chains (5 layers):** `F0→W2→W5→W7→W13` and `F0→W2/W6→W10→W11→W13`.
- **W5/W6 cycle:** the gap review wants the fence instantiated behind the gate. That is broken by F0: the fence ports are built standalone, and instantiating them is part of W5.
- **W2 is on every chain.** It is the single most valuable first RTL item.

## 2. Minimal GPU-comparator configuration

The consumer class is C0: an HBM read lands in both RF copies and a SIMD consumer reads it. The same chain serves KV_read.

**Required:** F0, W2, W4, W6, W5 and W10, plus subsets of W7, W11 and W13.
- W2: the read half is mandatory; the write ready costs almost nothing in the same successor.
- W5: per-SM entries only, with one contender class.
- W10: request, return and reverse channels.
- W7: replay of one emitted program.
- W11 subset: read backend gap, credit return and CDC terms.
- W13 subset: the two-ACK model mismatch, the 0-cycle structural_frontier retire, `cost_addition=0` and the stall-0 defaults.

| step | W | GPU analogue |
|---|---|---|
| owner + lease | W5 | warp scoreboard entry plus LSU/TMA request id (mbarrier expect_tx) |
| requester-allocated tag, exact completion | F0, W2 | MSHR index / AXI-ID, CHI TxnID; slot freed only on fill |
| both RF copies accepted, common ACK | W4 | RF writeback of a load return; TMEM `tcgen05.commit` |
| visibility → consumption | W6 | scoreboard release, mbarrier complete_tx, then try_wait |
| reverse retirement | W6+W5 | CUTLASS `consumer_release` (empty-barrier arrive) |
| CDC | W10 | async FIFOs between the GPC clock and the XBAR/L2/FBP clock |

**Deferred, and why that is safe:**
- **W1, W3:** the r14 provider is the ROM persistent-KV vehicle, not the comparator path. W1 is still trivial and independent, so do it anyway.
- **W8:** write class. W2 faults on any unexpected write-done.
- **W9:** L2 bank entries stay at ENABLE=0.
- **W12:** each per-SM entry has a single contender, and the PC service is already round-robin (`ot_hdc_qwen_pc_service.sv:60-67,94`).

## 3. Field sizing from source

The 324-bit software key is defined at `tools/h3_complete_native_calendar_installed_r2.py:164-165`. Only **20 of its 324 bits** are hardware:

| field | software bits | hardware bits | reason |
|---|---|---|---|
| generation | 64 | 1 | |
| sequence | 40 | 0 | software-only |
| lease | 64 | 0 | it is the gate entry index |
| provider_reference | 32 | 0 | software-only |
| rank | 7 | 0 | implicit in the die-local gate |
| PC | 12 | 0 | taken from address bits [6:0] |
| client_tag | 32 | 6 | |
| address_sector | 29 | 0 | already in the request |
| SRAM_bank_ACK_mask | 32 | 1 | the RF returns one combined ACK (`rf_service.sv:46`) |
| SM, client, phase, write | 5, 3, 3, 1 | same | |

The r14 `identity_t` has the same problem: 149 of its 192 bits are journal witnesses (`ot_hbm_r14_pkg.sv:4-9`).

**Generation width** follows ceil(log2(outstanding/ring))+1. It comes to **1 bit** everywhere a slot is freed only on exact completion or held through reverse. That covers:
- the PC service: 16 outstanding over 16 slots;
- the owner gate;
- the RF ACK, which has one outstanding write (`rf_service.sv:18`);
- r14: 3,072 live over 4,096 tags.

Freeing the slot at reverse *send* would need 4 bits, because of the 5 messages that can be in flight across the CDC bridge.

**Tag width:** a requester-allocated **16-bit wire tag** is enough:
- the PC level needs client 3 + SM 5 + slot 4 + gen 1 = 13 bits;
- the coalescer tag `{client6,slot6,gen4}` (`uarch_qwen_hbm_ingress.py:65`) is already 16 bits;
- r14 already reserves 16 wire bits, with the top 4 at zero (`ot_hbm_r14_tag_owner.sv:3`).

**Storage, W2 table:** 36,864 bits per die (valid, we, gen per slot, indexed by slot). The proposed `{tag32,gen,we}` table would be 417,792 bits, and the 324-bit envelope is 3,981,312 bits.

**Storage, W5 gate:** 30 bits per SM entry and 58 per bank entry, which is 2,816 bits per die, about 0.0016 mm² as flip-flops.

**Wire traffic at the 2,763 B/cycle ceiling** (86 beats per cycle per die):

| tag on the wire | tag bits per cycle per die |
|---|---|
| minimal 16-bit tag | 1,382 |
| today's 35-bit PTAGW | 3,022 |
| 324-bit key | 27,976 (more than the 22,105 data bits) |

**L2 endpoint tracks** (formula at `h4_hbm_gateway_constructive.py:218`):

| headers (request + reverse) | demand tracks | margin |
|---|---|---|
| current, 322 + 254 bits | 11,072 | 1,847 |
| minimal, 67 + 30 bits | 7,240 | 5,679 |

Both are against 12,919 available tracks (`final_handoff_r10.json`).

**New finding:** the priced ingress CDC is 32 pairs × 320 bits, one entry per cycle. That carries only 1,024 B/cycle per die: 37% of the service ceiling and 25% of the 128 B/clk SM ingest (`uarch_model.py:1599`). The return FIFO needs 4 × 277 bits per SM. At depth 16 that is about 743 kbit per die as flip-flops (0.43 mm²) against the 328 kbit priced today. This must be re-priced before W10.

## 4. Model inputs required before any RTL (per W)

The full list is under `model_inputs_per_W` in the JSON. The main ones:
- **Latency-neutral items.** W2 (slot-indexed table), W3 (folds into the 12-edge lookup and spare context bits) and W4 (same `write_go` edge) add 0 cycles.
- **W5:** needs a source-pinned positive edge count for each hold term. Arbitration wait is (contenders-1)×(hold+1).
- **W6:** must replace the 0-duration frontier with at least 2 edges.
- **W8:** a single-outstanding RMW costs about 1,152 × 790 cycles, roughly 0.76 ms per token per die. The model must size outstanding depth, or show that writing whole 128-byte head rows avoids RMW.
- **W10:** width and depth as in the finding above.
- **W11, W13:** these supply measured terms, not hardware.
