# Ordinary DCAL BC3safe source candidate

Source **190b12e9f** adds separately named `qkd_d2d_cal_seq_pin_bc3safe` and `ot_qwen_d2d_cal_seq_bc3safe`. It leaves the original sources, modules, defaults, physical specs and views byte unchanged. It is opt-in by explicitly selecting the new module and sources. No CTS, route, physical gate, REVIEW or submission ran; parent adoption remains unqualified.

The exact ordinary reference is frozen source569419a7d / CLOSED record43122e84b. Its unchanged actual generated `frozen_outer_wrapper.v` is included byte-for-byte. The reference core is the original source with only its module declaration renamed to the wrapper's `__ot_pr_core` name. Both original primitive and wrapper hashes are in `supported_profile.json` and `source_manifest.json`.

The outer generated landing uses **two synchronous stages for both assertion and release**. The original RTL then uses an asynchronous-assert/two-edge-release chain. BC3safe owns those same four stages explicitly: one outer first stage/four kept second-stage copies; one inner first stage/19 kept second-stage copies. Input capture, payload reset values, output/reset/data/program edges, counters and all sticky faults retain the full frozen-wrapper behavior. No HOLD/IGNORE, clock uncertainty, mask, ready/credit, delayed status or latency adjustment is introduced. Repeated reset/control and invalid-payload data are compared at every public output, including inactive payload bits.

`gen_dcal_bc3safe.py` generates behavioral next-state and sliced register blocks from the hash-pinned original source; it does not fork a mapped netlist. Per-use copies of layer/image indices, init/running flags, epoch history and merge qualifiers retain identical state transitions. Next-state logic reads old state exactly as the original nonblocking assignments did. Scalar/sliced flops retain their reset values. The generator refuses changed source/image bytes. `ot_keep_regs.tcl` is the same existing frozen canonicalization hook: it preserves cells driving keep wires before optimization and does not replace sequential behavior. Omitting it was independently observed to collapse replicas and retain the original206-load reset fault; that failed exploratory census is retained remotely.

## Measured source-only results

| Item | Frozen wrapper, same source-only recipe | BC3safe |
|---|---:|---:|
| Flops / clock sinks | 253 | 351 |
| Mapped standard-cell area | 214um2 | 259um2 |
| Recursive functional first-logic maximum | 206 | **28** |
| Functional sources above32 | present | **0** |
| External raw reset first-logic loads | 1 | 1 |
| Outer first-stage Q/shared D | 1 | 4 |
| Outer second-stage reset loads | 45 | maximum23 |
| Inner first-stage Q/shared D | 1 | 19 |
| Inner second-stage reset loads | 206 | maximum16 |

The census follows INV/BUF cells to actual first logic, counts true source drivers and external input pins, and records every sink. It includes upstream data inputs of new copies and both reset levels; clock sinks are separately recorded. Candidate actual1_synth ODB SHA is `c6a86fb5628cdb9cc1c84c8b89f2b8408507f43ef7cd0fe947b1bbe47571ad04`. Both actual mapped netlists are retained as deterministic gzip artifacts. All source/lib-flow identity and evidence hashes are retained.

**Static tie obligation remains:** the source-only ORFS netlist has one TIEHI with347 static loads, separately listed in the census. Normal physical tie replication must discharge that constant net before physical admission; the functional max28 statement excludes this static tie and the clock. This packet does not claim every nonclock physical net meets32. It does not install a fanout waiver.

The unified model function `qwen_kv_dcal_bc3safe_model` prices up to113 additional flops before the replicated implementation (366 source-state/pipeline-bit upper bound); measured mapping adds98 flops and45um2 under the same recipe. The original closed physical recipe's265um2 includes its own flow/physical context, so259um2 versus265um2 is not a like-for-like area saving. The old21.6x34.56 frame and its old native timing are not inherited. The added98 clock sinks, tie replication, pin access, loaded reset/clock geometry, placed occupancy, native clock extrema and actual parent slot all require measured review before any gate. Token latency delta is0 and throughput is unchanged; no token-rate improvement or release qualification is claimed.

## Exact behavior and negative witnesses

Fleet-unpinned `ot-run`, Verilator5.050, actual ordinary shape:

* Full frozen-wrapper independent miter: **600,000 edges**, every one of53 public bits, **80 reset edges**, **117 calendar starts**, **305,320 sticky-fault edges**. It drives the exact66 boot words before the production epochs, then adversarial payload, reload, halt, epoch and reset activity. PASS.
* Full original boot/calendar bench with only the candidate module name and its structural monitor path adapted: **66 boot writes,2 admissions,2 token starts,36 layers,2809 calendar events,6 runtime writes**. It contains the real boot dispatcher and actual TX/RX calendar engines. PASS.
* All five frozen recipe mutants fail with actual witnesses: dropped sequencer writes replay SEG2; stale non-MU image; colliding boot/sequencer writes (COL); boot write while running (RUN); missing RX base (EARLY). No build failure is used as a mutant witness.
* Independent full-wrapper reset-stage, reset-value and payload-reset mutants fail at the comparator. Unsupported EP_SKEW2, GO_OFS1 and nonzero START_ADJ fail explicitly at elaborated runtime. Primitive/image hash-corruption negatives are refused by the generator before source generation.

The final actual units are oth-ubuntu-1534321-1792431751 (independent synthesis/census),1534322-1792431751 (miter and six negatives),1537500-1792431833 (final production bench/five mutants and clock census), and the source-only baseline/profile unit recorded in `baseline_profile.log`. All are terminal. Prior failed exploratory output directories remain remote and no failure was overwritten.

## Exact profile and parent fault contract

This is **historical ordinary AW11/32-entry, MU=1, EP_SKEW3, GO_OFS0, START_ADJ0, production MUT0**, with token period249600/first-token1176 and the frozen image's **K TXDP0x03030415**. MUT1 is bench-only. `supported_profile.json` records the exact primitive/image SHA and continuous fault contract. It cannot qualify expanded OVL AW12 or a substituted image.

The next production epoch needs a separate coherent ordinary **codec2 K0x03030416** image/source/certificate and qualification: known image generation recipe `D2D_DIE_STAGES=2,2,2,3,2,2/11,11,9,9,9,9,9 D2D_KV_CODEC=2 D2D_MU=1` (prior image source1a73e1e7a, image_mu SHA prefixe7d4d2d0). This packet does not substitute that image. Expanded OVL remains owned by the OVL lane.

`fault` continuously preserves the original sticky OR of sequencer/COL/RUN/STALE/EARLY; it clears only under the inherited full-wrapper reset and is never qualified by ready, status, retirement or a quiet interval. **Parent wiring must unconditionally consume this fault in the actual sticky fault fold and price its reset/clear and observation path.** Actual GEN7 has DCAL fault unread, independently of this source repair. That missing consumer, native relative clock/reset bounds and final admission/STATUS integration remain open. The new source is not a permission to mask or ignore any fault.
