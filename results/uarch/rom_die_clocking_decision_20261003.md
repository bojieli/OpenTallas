# ROM-die clock distribution: decision (2026-10-03, model only)

Record: [`rom_die_clocking_decision_20261003.json`](rom_die_clocking_decision_20261003.json). Tool: `python3 tools/rom_die_clocking_model.py --output <json>` (about 30 s; reads `tools/uarch_model.py` without editing it). No P&R was run. Each constant is labelled MEASURED, MODEL or ASSUMED.

**Measured starting point.** The Qwen full die is 792.36 mm². A single H-tree across it diverges at the root by 0.38 / 1.5 / 2.9 ns (thick metal / TT routed / SS routed, 5 % OCV); see `clock_trunk.json` @ c3a56754. One synchronous die tree is therefore impossible. Every link is pipelined at ≤ 430.56 µm, so a stage only sees the skew between its own two flops. Skew matters only where physically adjacent leaves diverge high in the tree, at the split lines.
- **A** puts FIFOs everywhere.
- **B** erases the split lines with a mesh.
- **C** puts FIFOs only at region boundaries ≤ 5.25 mm, which is the measured 60 ps H-tree extent.

**Crossings a token** come from the composed model: +10-cycle probes on every op class.
- Qwen TP-4: **217 ME ops**, 72 all-reduces and 36 near-HBM attention round trips.
- DS ROM: **282 field matvecs**, 49 streamed attention/index ops, 80 all-reduces and 73 stage hops (S73).

| Option | Qwen added cycles | Qwen rate, calibrated / near-HBM (bound) | DS added cycles | DS rate (bound) | FIFO area, Qwen | Clock distribution | Risk |
|---|---:|---|---:|---|---:|---|---|
| A: GALS, one tree per hardened element | 15,396 | −3.46 % / −6.30 % (−6.79 %) | 8,737 | −1.78 % (−2.12 %; −2.34 % on expert paths) | 7.9 mm² | 0.55 W | about 60 crossings an ME op; per-cycle and credit loops gain FIFO latency |
| B: global mesh plus local trees | 0 | 0 | 0 | 0 | 0 | 2.9 W (1.6–4.1 W) **ungatable** | **High.** The flow has no mesh synthesis or multi-driver clock timing. Period jitter is about 65 ps at 9 mV a cycle on the core rail, which exceeds the 60 ps budget. |
| **C: mesochronous regions plus forwarded link clocks** | **506** | **−0.12 % / −0.22 %** (−0.88 %) | **661** | **−0.14 %** (−0.55 %) | 2.5 mm² (of 22.6 mm² margin) | 0.1 W trunk + 0.9 W forwarded clocks (gateable) | Medium-low: per-region CTS, one new FIFO primitive |

**Notes on the table.**
- **Crossing cost.** A mesochronous crossing costs Δ = 1 cycle when the wander (5 % of the non-shared insertion) fits half a period. That holds for thick metal, 192 ps, at depth 4. The TT-routed case costs 3 cycles and the SS-routed bound 4, both at depth 8.
- **Skew.** All options still close under the 60/25 ps policy. In C, a region's internal split is ≤ 48 ps (setup), and the few buses that cross it are hold-fixed by STA. Wander between regions is absorbed by the FIFO window, not by the uncertainty.
- **Jitter.** Any distribution of about 4 ns insertion, whether B's mesh-driver tree or C's trunk, gives 14 / 31 / 62 ps of supply-induced period jitter at 2 / 4.5 / 9 mV a cycle. C's trunk drives about 130 loads (0.1 W), so it moves cheaply onto a filtered clock rail. B's mesh plus driver tree is about 5 nF on the core rail.
- **Metastability.** Mesochronous FIFOs need no steady-state synchroniser: the pointer is placed at reset, and a monitor fails closed. Truly asynchronous crossings (HBM, UCIe/SerDes, die-to-die) need 3 flip-flops. With 2 flip-flops at τ = 20 ps the system MTBF is about 6 weeks for Qwen and about 2 days for the DS array. This costs +180 / +350 cycles a token, the same in every option and under 0.1 %.

## Recommendation: C on both dies

- **A is rejected.** It costs 1.8–6.3 % of per-user rate, against the latency-first objective.
- **B is rejected.** Its whole gain over C is 0.12–0.22 % (Qwen) and 0.14 % (DS). That is below the 1 % adoption gate, and B carries physical-design and sign-off risk that AGENTS.md excludes.
- **Practice supports C.**
  - Mesochronous tiles: Intel 80-tile, Vangal JSSC 2008.
  - FIFO-joined frequency domains: Intel SCC (Howard JSSC 2011); AMD core, fabric and memory clocks (Naffziger ISCA 2021); NVIDIA research fine-grained GALS (Fojtik ASYNC 2019).
  - Mesh with deskew, the alternative: IBM (Restle JSSC 2001) and Intel (Kurd JSSC 2001; Tam JSSC 2000), on custom flows.
  - H100/B200 and Cerebras on-die clocking is not published, and nothing here relies on it.

**Price to report into the model** (`price_to_model`):
- **Qwen ROM:** +2Δ cycles on every ME op (tile tap + tree top) and +2Δ on each attention round trip. Central: **+506 cycles = 0.42 µs a token**. Bound: 2,024 cycles. A banded tree top adds +217 cycles, and unmerged IO FIFOs +144.
- **DS ROM:** +2Δ on every field matvec and every streamed op. Central: **+661 cycles = 0.55 µs**. Bound: 2,642 cycles. Unmerged hop/all-reduce FIFOs give 967 cycles.

## What Codex implements

1. **`rtl/common/ot_meso_fifo.sv`.** Forwarded write clock, region read clock.
   - Reset handshake: DOWN → WAIT → RUN, as in `ot_ratio_cdc_fifo`.
   - Read pointer placed from a 3-FF-synchronised sample. No steady-state synchroniser.
   - DEPTH 4 (8 at the bound), credit return, and a sticky fail-closed drift monitor.
   - Gates: a dual-clock bench sweeping phase 0..T and wander ±w, plus mutants; ORFS at W = 512, D4, SS 60 ps / FF 25 ps.
2. **`rtl/common/ot_fwd_link_stage.sv`.** A data plus forwarded-clock stage at ≤ 430.56 µm.
   - Opposite-edge capture for hold.
   - SDC generated clocks; the clock is routed as a shielded clock net beside its bus.
3. **Qwen RTL** (`TAP_MESO = 0` by default):
   - FIFOs: 1,536 tile-tap FIFOs (511 b), 96 block-word FIFOs at the tree top, and strip-return FIFOs.
   - The head chain and corridors become forwarded links from the hub x root.
   - Exact gate: bit-identical logits, VM and KV, with only cycle shifts.
4. **DS RTL:**
   - Entry and exit meso FIFOs on the field broadcast and return trees at about 36 regions of ≤ 4.9 mm.
   - The ratio CDC stays inside the hub region.
   - The hub sides of the die-to-die and IO async FIFOs move to the hub edge.
   - Off by default; the exact gate runs on L0 and L20.
5. **`ot_async_fifo`** gets SYNC_STAGES = 3 on every asynchronous crossing.
6. **Physical:**
   - REGIONS/GROUPS per clock region, and one OpenROAD CTS run per region root.
   - A shielded M8/M9 trunk of ≤ 130 leaves. The trunk and the forwarded clocks run on a filtered clock rail (LDO).
   - SDC: a `create_clock` at 0.833 ns per region, asynchronous groups between regions, and `set_max_delay -datapath_only` of 1 period on FIFO arcs.
7. **Model:** add the CLOCK_REGION term to `tools/uarch_model.py`, then re-price with the Δ the bench measures.
8. **Characterisation:** run SPICE on the ASAP7 synchroniser τ at SS.

Do not build a clock mesh, and do not split below the hardened block.
