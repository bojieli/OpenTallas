# HBM accelerator handoff — VALIDATION-FIRST ADDENDUM (binding; owner directive 2026-10-03)

The ladder in HBM_ACCELERATOR_HANDOFF.md (study a3ed9c36d) is a MODEL. Several rungs use borrowed or assumed constants (marked ESTIMATE), and none has been implemented, placed, routed or measured. Treat every modelled gain as a **hypothesis to be proven**. Do not quote 3,015 / 6,001 tok/s (DS) or 2,391 / 7,493 (Qwen) as results anywhere until the measured composition replaces them.

## What usually goes wrong, and must be measured for every rung
1. **Area.** New units (arrival counters, link endpoints, per-stack scorers, select units, look-ahead logic, deeper FIFOs) cost area. Re-run the die area ledger with each rung, including routing, power grid, clock tree and repeaters. Check it fits the reticle at the target utilisation (route-feasible ~0.7, timing usually binds).
2. **Place and route.** Wide buses (collective endpoints, cut-through paths, scorer outputs, engine-write taps) can overflow channels. Every new boundary needs a corridor/track check and a routed element, using the macro-alignment check and the corridor-gate lessons: pins centred, long haul off M3/M5, stage length ≤ ~430 µm.
3. **Timing.** Each rung must close at SS setup (60 ps) and FF hold (25 ps) in context, with no relaxation. The control-loop study already found SM issue at 750–815 MHz, bulk-copy consume at 590–680 MHz, the SECDED fence at 429 MHz and KV lifecycle at 458 MHz as built. Fix them with look-ahead or registered flags, never by halving throughput. A placed-screen miss under ~150 ps means route it before concluding.
4. **Latency of dependent stages.** Measured costs have repeatedly come in above the model:
   - Qwen layer: 28% over;
   - DS collective in-package step: 83 vs 10 ns;
   - edge-scorer merge: 490–745 vs 161 cycles;
   - verify per extra position: +1,556 vs ~1,100;
   - real memory: +300–1,100 cycles per layer.

   Measure every rung's latency in RTL on the serial critical path, including wire stages, clock-crossing FIFOs, credit loops and refresh interactions, not as a standalone best case.
5. **Interactions.** Gains don't simply add up: e.g. a cut-through collective removes overlap that the fused epilogue assumed, or refresh collides with expert fetch. Re-measure the composition after each rung lands, not just the rung alone.
6. **Clock-domain crossings.** Any new crossing (HBM service clock ↔ SM/streaming clock, serial domain) adds measured FIFO latency (~1.6–1.7 cycles for the related-clock FIFO; more for async). Count it.
7. **Exactness.** Every rung is default-off until bit-exact against the golden on the real program, including faults and corner cases. Failed gates are preserved, never overwritten (e.g. the two failed Qwen fused-epilogue gates).

## Required per-rung gates (in order; a rung is ADOPTED only when all pass)
G-exact (bit-exact RTL) → G-latency (measured in system context on the critical path) → G-area (ledger and fit) → G-route (routed element, corridor check) → G-timing (SS/FF in context) → G-gain (measured per-user rate gain ≥ 1% after composition). A rung that measures slower, doesn't fit or doesn't close is REJECTED and recorded, not tuned around (AGENTS.md).

## Reporting
For each rung, report: modelled gain, measured gain, the difference and its cause; area, route and timing status. Keep a running "measured composition" table that replaces model numbers as rungs land. The published HBM-accelerator figures are the measured composition only, with unmeasured rungs listed as excluded.

## Priorities given the risks
Start with the rungs that have the largest modelled gain AND the highest risk, so problems surface early:
- **HA2:** direct links and topology, 70 µs.
- **HA6 / control loops:** clock fixes. Without them the SM runs at ~0.6 GHz and all gains are moot.
- **HA1:** barrier, 8.9 µs, low risk.
- **HA8:** the Qwen full token through the canonical launcher, to give a measured baseline.
- **Then HA3–HA5.**

Use all hosts per FLEET_AND_FLOW.md with admission guards; no model inference on CPU hosts.
