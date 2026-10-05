# Qwen3-8B ROM cooling recheck at HEAD dcba5c0ab (model-only)

**Design:** option C (`tools/uarch_model.py:2252-2258`). Two packages of two dies, TP-4, 4 HBM3E stacks per die, INT8 weights, 8K FP8 KV, batch-1 AR, no ROM ECC.

**Power model:** P_die(r) = static + E_dyn × r. The cap is the lower of two checks: the die check against the per-die limit, and the package check (2 dies plus their stacks at 3.92 pJ/bit; `tools/power_scenarios.py:182-199`).

**Clock:** 1.2 GHz, the streaming-domain target in AGENTS.md. 1.0986 GHz is given as a sensitivity.

**Replay:** `recheck.py` (same directory) reads the HEAD constants through `power_scenarios`/`uarch_model` and recomputes everything.

## Per-die terms (per token)

| term | A (mJ) | B (mJ) | constant, cite, grade |
|---|---|---|---|
| HBM controller/PHY/IO, 150,847,488 B × 10.19 pJ/bit | 12.30 | 12.30 | power_scenarios.json:305-323, **unqualified derived** |
| MAC, weights (1.892 G) + attention (0.604 G) | 9.92 | 1.47 | A 3.974 pJ measured-ours TT (:163-169). B 0.59 pJ published-spec (:230-243) |
| KV ring SRAM ×2 + delivery | 0.82 | 0.82 | :347-353 published-measured floor. :340-346 assumed |
| ROM read + delivery, 1.893 GB | 0.59 | 0.59 | :333-339, 0.08 pJ/B **assumed** |
| stream unit | 0.25 | 0.25 | :354-360 published-spec |
| TP-4 board exchange | 0.09 | 0.09 | :398-405 published-measured |
| **dynamic total** | **23.96** | **15.51** | |

**Static per die: 51.6 W**
- Leakage 18.98 W: logic 173.8 mm² × 0.10, ROM 220.7 mm² × 0.0067, SRAM 23.9 mm² × 0.005. Source :374-397, assumed.
- ICG-gated clock 21.47 W: 8.5e-11 J/mm²/cycle × 1.2 GHz, with 0.15 on the ROM and SRAM arrays. Source :361-373, assumed.
- HBM idle 11.2 W: 4 × 2.8 W. Source :324-330, assumed.
- The ungated `clock_w` of `power_ledger` is not used.

## Die power and caps (tok/s)

| | 2,789 (358.6 µs) | 3,564 (280.6 µs) | 9,368 (uarch b1) | cap, liquid 474.6 W | cap, air 374.6 W |
|---|---|---|---|---|---|
| A | 118.5 W | 137.0 W | 276.1 W | **17,650** (die) | **13,476** (die) |
| B | 94.9 W | 106.9 W | 197.0 W | **27,086** (package) | **20,814** (die) |

**Sensitivities (A liquid / A air):**

| sensitivity | A liquid | A air |
|---|---|---|
| GH200 die share 8.23 pJ/bit | 19,583 | 14,952 |
| I/O-only die share 0.8 pJ/bit | 31,586 | 25,567 |
| ROM macro liberty energy (7.41 pJ/read, `ot_rom_4096x266_m8_tt.lib:93`) | 17,441 | 13,317 |
| 1.0986 GHz | 17,725 | 13,552 |
| Measured routed clock density (9.31e-10, energy_per_token.json:671) gated to lane-busy time | 14,648 | **11,184** (worst valid case) |

**Clock gating is mandatory.** With the clock ungated (logic 194 W + 28,795 ROM macros × 7.41 pJ × 1.2 GHz = 256 W), static is 480 W, which is above the liquid limit, so no token rate is possible. Qwen therefore needs per-group and per-ROM-macro clock gating, just as V4.1 does.

## Verdict

- **The 3,271/5,278 cap is not valid at HEAD.** It was computed for one reticle carrying the whole model's KV, against the withdrawn 407.5 W limit at 9.66 pJ/bit. TP-4 over 16 stacks cuts each die's HBM die-share term to 12.3 mJ/token.
- **Cooling does not bind at 2.79k or 3.56k.** The headroom is 4.8-6.3x and 3.8-5.0x respectively, and 3.1x even in the worst valid sensitivity.
- **Where cooling starts to bind:** about 17.7k tok/s (A liquid), 13.5k (A air), 27.1k (B liquid) and 20.8k (B air). The 9.37k model rate also fits, with 1.9x headroom in A liquid.
- **Saturated batches:** the KV-stream bound is 23,842 tok/s. Cooling, not KV bandwidth, would cap aggregate throughput in A (both classes) and in B air.
- **Effect of removing ECC:** ROM area goes from 229.3 to 220.7 mm² per die. That is about −0.06 W of leakage and −0.2 W of clock, so the cap moves by less than 0.2%. Neither model charged check bits on reads, and ECC decode energy was never priced.
- **Near-HBM attention:** this takes 15.5 mJ off the logic die, so A liquid would reach about 50k. The heat moves to the stack base dies, though, and no thermal limit for those exists in the repository.

## Defects found (not fixed, read-only)

1. `results/arch/power_scenarios.json` and `qwen_point` (`power_scenarios.json:415-457`) still price the superseded O4 design point: 2 dies, 8 stacks, 302 MB of KV per die. They report 7,859 (A liquid), 5,766 (A air), 12,160 (B liquid) and 8,921 (B air). These figures are stale too.
2. `uarch_model.qwen_rom_economics` charges the die only 0.8 pJ/bit (`tools/uarch_model.py:434, 2287, 2290`). The controller/PHY share goes into "stack", which is the boundary error that finding 3 corrected. Its ROM area also still includes SECDED (`:4831, 4854`).
3. The largest term, the HBM die share (51% of A dynamic and 79% of B), has no sourced value.
