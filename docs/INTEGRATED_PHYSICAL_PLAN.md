# Integrated design plan: build and close what the model sized (revised 2026-09-30)

Root: Claude (`claude-main`). The binding method, sign-off corners and clock domains are in [AGENTS.md](../AGENTS.md). The architecture is Atlas Table 5-2 ([ARCHITECTURE_ATLAS.html](ARCHITECTURE_ATLAS.html)), and the model is [MICROARCH_MODEL.md](MICROARCH_MODEL.md).

**Objective order:** minimum single-user decode latency first, then aggregate throughput from independent requests. Exact arithmetic is mandatory.

## How we got here

Until 2026-09-29, independently verified components (exact engines, routed microblocks, reservation floorplans) missed the latency target once composed, sometimes by orders of magnitude. Place and route was being used to discover the architecture. The correction was a unified microarchitecture analytical model (`tools/uarch_model.py`) covering Qwen3-8B ROM, Qwen3-8B HBM, DeepSeek-V4.1 ROM and DeepSeek-V4.1 HBM. It came first, and only what it sizes gets built: floorplan, then one hardened element sized to the full goal, then replicas.

That phase is complete. Every design now has a chosen element, count, network and floorplan in the model. The current phase builds those elements, closes them at the adopted sign-off, and runs full-shape tokens through them.

## Adopted decisions (2026-09-29/30)

- **Sign-off:**
  - Setup at SS and hold at FF, with 60 ps / 25 ps uncertainty.
  - TT results are pathfinding only.
  - Memory macros are checked at SS with their own clock-to-q.
  - Arithmetic primitives are qualified in context: `(* keep *)` prefix adders, and the ASAP7 adder map off by default.
- **Clock:** 1.2 GHz at SS. The V4.1 ROM die has two domains: 1.2 GHz streaming and 0.9 GHz for the serial chain. One PLL at 3.6 GHz feeds them through /3 and /4, with ratio FIFOs between them.
- **Wire:** 504 µm per registered stage at 1.2 GHz SS and 748 at 0.9 GHz. We accept this cost with free fixes only; there is no large architecture change.
- **V4.1 ROM:**
  - Dedicated BF16 columns: the plain q pair plus 1,024 BF16 column pairs, giving 37 stages on 188 dies.
  - Layer dies use 4096-row macros in ping-pong, 2 per slot; head dies use 8192-row macros in ping-pong.
  - A per-pair ICG, which also stops the macro clock, is mandatory.
  - Current is managed by a 50% concurrency cap and a 256-cycle pre-ramp. This requires a package loop inductance of at most 2 pH per die.
  - MTP runs at m=1.
- **Qwen ROM, option C:**
  - Four dies in two B200-class packages, TP-4, with G=6,144 per die.
  - INT8 weights with a BF16 row scale, and FP8 KV.
  - Autoregressive only.
- **Density:** storage-only 75 Mbit/mm² at N5 plus ECC 266/256, for every die class.
  - The ROMA-derived 57.8 is the conservative sensitivity.
  - Compute-in-ROM at 148 is an upside only.
  - HC1 is a whole-die cross-check, not an anchor.
- **Context:** 1M is the headline and 200K secondary. The reference token is seed 20260930, token 21946, margin 3.149.
- **MTP acceptance:** third-party τ = 3.78, from V4-Flash arena-hard general chat (LMSYS DSpark, cap-accept ceiling). The sensitivities are 5.24 and 2.91. Our 3.649 is corroboration.
- **V4.1 positioning:**
  - Saturated throughput, energy and cost at equal cost are the headline.
  - Per-user speed is claimed against real GPUs (tiers 1–2) and reported honestly against the idealised tier 3.
  - The ROM design goal is maximum per-user rate; die count is free.
- **Headlines stay pending** until calibration, then are restated together (priority 4).

## Priorities

### 1. 1.2 GHz SS closure of every element

Close setup at SS and hold at FF at 0.833 ns (or 1.111 ns in the serial domain). Each block that misses is pipelined or parallelised, and every added cycle goes back into the model.

- **Already closed at SS 1.2 GHz:**
  - K-arbiter pslice, ratio FIFO, pg_ctrl, droop controller, pre-ramp and concurrency cap (`results/physical_abi3/asap7/chip/v41_w18/harden_1p2/`);
  - the LAT-7 FP32 add and LAT-6 multiply (`results/physical_abi3/asap7/hdc/w11_fp/w11_fp_latency_sweep.json`), with in-context qualification pending;
  - several streaming micro-units.
- **Open, highest first:**
  - the BF16 column element (W10);
  - the V4.1 q pair, −50 ps before placement (W10);
  - the SU lanes, at 709 MHz against 1.111 ns (W11);
  - softplus, at 734 MHz (W11);
  - the attention controller, −429 ps (W11);
  - the K-arbiter region, −313 ps, with a two-head fix (W18b / W15b);
  - the HBM SM columns (W13b).

**Exit:** every element of all four designs is closed at SS/FF with a committed record, and the model carries the measured latencies.

### 2. Full-shape RTL tokens

- **V4.1 ROM (W17):**
  - Done: the TP-4 layer 0 is bit-exact at ISA level at 1M and 200K (`results/rtl/w17_l0_fullshape_isa.json`), and the field composition gate passes 160/160.
  - Next: the four-die layer-0 RTL run is in progress, then an indexed layer, then the full token against 21946.
- **Qwen ROM (W12b):**
  - Done: TP-2 layer 0 is exact at G=6,144, the full token is exact through layer 9, and the TP-4 ISA oracle gives 50994.
  - Next: the TP-4 RTL token is compiling.
- **HBM comparator (W19):**
  - Done: the TP-96 full token (40 layers plus head at 1M → 21946) is bit-exact at ISA level (`results/rtl/w19_hbm_tp96_isa.json`), and the feasibility audit is done (`results/uarch/hbm_feasibility_audit.json`).
  - Next: expert-fetch RTL against a DRAM model, the MTP golden, then runtime composition over 96 ranks.

**Exit:** one full-shape token per design, bit-exact in RTL against the reference, with its cycle count fed to the model.

### 3. V4.1 die rebase on p12 with the BF16 columns (W18b, with W10)

Rebase the die assembly once, on the p12 q-pair tile (476 × 126.9 µm) and the BF16 column element. Then re-run the placement, the channel global route, the crossings and the IR stack. Adopt the recommended IR fix: element M5 ×2 plus half the bumps on VDD/VSS, 65.8 mV against 70. Apply the free wire fixes: the collective engine at the link edge with a lane map, and the distance-aware bank map.

**Exit:** a die record on the final element, with zero overflow and the IR budget met.

### 4. Headline restatement (W16)

W16 regenerates `results/uarch/*` on the calibrated model: the adopted clocks, the 188-die V4.1 ROM, Qwen option C, the audited HBM comparators, and τ 3.78. The Atlas abstract, Table 2-1 and §8 are then restated together. Until then every headline is written as "≈ … (pending restatement)". The current estimates are:

- V4.1 ROM: ≈3,388 AR / ≈5,170 MTP, ≈90.0k saturated;
- V4.1 HBM tier 3: ≈2,230 / ≈5,230;
- 8× B200: 278 / 539;
- Qwen ROM C: ≈9,700;
- Qwen HBM: 881 AR, ≈2,300 DFlash.

## Streams and owners

| Stream | Owner scope | Next deliverable |
|---|---|---|
| W10 | V4.1 element: q pair + BF16 column element at 1.2 GHz, p12 tile, element PDN | BF16 column element and q pair closed at SS/FF |
| W11 | V4.1 hub units: VM-H landing, selected CKV, ILV option (a), serial/streaming closure, shared FP primitives | SU lanes, softplus and attention controller closed; ILV (a) exact |
| W12b | Qwen ROM: TP-4 token, tile, die, droop | TP-4 RTL token; die droop analysis |
| W13b | HBM SMs | SM columns closed at SS |
| W15b | Collectives and links: SS campaign, switch TP-96 record, thick metal | committed P = 6 / 48 NVLS records |
| W16 | uarch model and records | regenerated `results/uarch/*`; restated headlines |
| W17 | V4.1 full-shape token: L0 4-die RTL, then indexed layer, then full | L0 4-die RTL run exact |
| W18b | V4.1 die assembly: one rebase on p12 | die record on the final element |
| W19 | HBM full-shape token: ISA done; expert fetch RTL, MTP golden, composition | expert-fetch RTL with measured first-byte latency |

## Open risks

These are engineering risks unless marked otherwise.

1. 1.2 GHz SS closure of all elements; the highest is the BF16 column element.
2. Full-shape RTL tokens: the V4.1 L0 run is in progress and the Qwen TP-4 token is compiling.
3. The IR margin is 4.2 mV.
4. Qwen droop analysis (assigned).
5. **Assumptions:**
   - ROM density;
   - package loop inductance ≤ 2 pH;
   - idealised tier-3 collectives;
   - ASAP7 as the physical basis.
6. **Fundamental ceilings:**
   - V4.1 per-user decode is latency-chain bound. The ROM leads HBM by about 1.5× autoregressive and ties with MTP.
   - HBM pays 265 collectives per token.

## Hosts

Long jobs run in pinned clean worktrees. Launch hosts:
- ot-pve1 and ot-pve2 (227 GB each);
- ot-pve3 (108 GB);
- the six AGIdocks (≤30 GB per job, via `/tmp/claude-1000/remote_gate.sh`);
- the local machine.
