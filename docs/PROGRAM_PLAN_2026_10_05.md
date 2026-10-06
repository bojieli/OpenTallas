# OpenTallas program plan: three design targets (2026-10-05)

This document aligns the owner, Claude and Codex on one picture: where the three targets stand, who owns what, the major risks, and the order of work. Every number cites a committed record. The measured scoreboard (`results/arch/measured_scoreboard/`, regenerated with `python3 tools/measured_scoreboard.py --check`) is the referee: when it disagrees with this document, the scoreboard wins.

## 1. Goal and closure definition

Close three design targets:

1. **Qwen3-8B ROM**, 8K context (position 8,191).
2. **DeepSeek-V4.1 ROM** (S81, 81 stages), 1M context (position 1,048,575).
3. **HBM accelerator**, both models at the same contexts.

A target is closed when all four hold:

- **Exact token:** a bit-exact, full-shape token at the target context.
- **Measured rate:** a per-user rate composed only from measured components (minimum component, one layer per type plus the head).
- **Physical feasibility:** at most 858 mm² per die, global route clean, SS setup ≥ 0 with 60 ps uncertainty and FF hold ≥ 0 with 25 ps uncertainty at 1.2 GHz, IR drop ≤ 35 mV.
- **Committed records.**

Owner rules in force:

- Measured compositions only.
- Every HBM load at ≥ 90% of peak.
- GPU baselines come from published third-party figures (`results/external/registry.json`).
- Acceptance (tau), owner decision 2026-10-05: DeepSeek-V4.1 uses **4.159**, the owner 6-class workload blend (harmonic, greedy, gamma 5; `results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json`), because the published V4.1 primary is a single GSM8K dataset and several published sources are V4-Flash, not V4.1. The published V4.1 value 3.8879 and range 3.43–4.32 are a sensitivity (`OT_TAU_SOURCE=third_party`). Qwen3-8B stays at the third-party derived 3.1445 (`tools/third_party_tau.py`).
- MTP is required where it pays.
- Mandatory baseline blocks must close: only optional levers face the ≥ 1% reject rule.
- Nothing heavy on localhost.
- Every live job has an owner in the experiment register.

## 2. Where each target stands

| Target | Headline (measured) | Exactness | Physical | Status |
|---|---|---|---|---|
| Qwen3-8B ROM, 8K | AR on STREAM4: **6,169.7 tok/s** (5,974.3 wire-bound); 2.99x the one-stack path (`results/rtl/qwen_rom_kv_fullbw_20261004/`) | All 4 dies and token K/V bit-exact vs GPU golden | Die 811.8 mm²; global route **closed** (b3r16B40, 0 overflow, `f1df64409`); IR 20–26 mV | Core decode −217 ps; port/scale slab share open; landing merge −0.75 ns |
| DeepSeek-V4.1 ROM, 1M | **1,654.7 AR / 4,872.2 MTP** (all measured: AR 604.3 µs, MTP step 853.6 µs; fused hc_post lever `9082d0a53`, head lever `1c4e785ee`, window bound `42cf43125`; tau 4.159, 4,554.6 MTP at the published 3.8879) | Every term bit-exact; 3 interaction bugs found and fixed (`952159dfa`, `be155754b`); no native end-to-end S81 token yet | S81 layer and head dies passed physical feasibility at `21fcf6469` (0 overflow, IR 28.6–32.2 mV), **before** the recovery levers; that netlist had connectivity holes (x chain undriven at 2,161 of 2,417 pairs, cfg ROMs and return nodes unclocked, no forwarded stages or meso FIFOs; die-top lint `7ccef3810`), now wired by the S81-DIE `--gen r8` generator | Recovery in progress; several blocks still closing |
| HBM accelerator, DS 1M | **2,173.7 AR / 4,683.2 MTP** (fully measured `7dfe62676`, notice default; tau 4.159, 4,377.9 at 3.8879). Matched reference `b39173b46` (review corrections measured, shared levers credited): **474.8 µs AR / 1,050.6 µs MTP step = 3,958.5 MTP** | Exact | Control loops closed (bulk copy, KV lifecycle `7ce508488`, SECDED fence `b5f1dcdf6`) | Datapath short of 1.2 GHz: collective endpoint −329 ps, SU lane −4.8/−46 ps, SFU tail −113/−167 ps, attention tile about 881 MHz |
| HBM accelerator, Qwen 8K | 2,154–2,220 AR; DSpark about 5,055 (TP4, `2f4a6af49`) | Exact (TP2 and TP4 vs GPU golden) | Not closed: Qwen-side core, collective and lane blocks open | Handed to Codex |

**Comparisons at equal silicon, measured:**

- **Qwen:** the ROM (AR, STREAM4) is about 2.7x the HBM accelerator's AR.
- **DeepSeek (per user):** against the fully measured HBM accelerator the ROM is 0.76x on AR and **1.04x on MTP**. Against the matched reference it is 0.79x on AR (604.3 vs 474.8 µs) and **1.23x on MTP** (step 853.6 vs 1,050.6 µs). Both ratios use one tau on both sides, so they do not depend on it.
- **Energy** (`results/arch/energy_silicon_measured/`, regenerated 2026-10-05):
  - Qwen ROM leads (0.109 vs 0.761 J/token, model power).
  - DS at batch 1, AR: ROM 5.80 J/token (measured PG residual) against HBM 5.77, a tie until spine gating is measured.

## 3. Decisions already taken

- **Qwen ROM operating mode is plain decoding (AR) at 8K.** This is conditional on `results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json`.
  - DSpark on the compute-balanced ROM measured 0.763x AR (free-draft bound 0.969x): the ROM's read rate equals its MAC rate, so a 4-position verify layer costs 3.26x an AR layer.
  - DSpark stays built and exact but off.
  - MTP stays required and pays on the DS ROM (2.94x) and the HBM accelerator (2.15x), both at tau 4.159.
  - Principle: speculation pays only when the dominant per-token cost is shared across the verified positions.
- **Near-HBM attention dropped** (`c8d7ab368`); the KV path is STREAM4. The old HBM_STREAM controller is retired.
- **DS ROM batched draft head (L2, NV5) rejected.** It is wire-bound: routed −674 ps.
- **Rejected optional levers** (recorded with measurements): HA3 cut-through, async collective (SB_PIPE 1–4), index row layout, 2,048-lane SU, edge-gap floorplan, Option A slab layering.
- **Fleet:** ot-epyc2 added as a twin of ot-epyc1tb (`4447740f7`); `admit.sh` runs on all four remote hosts.

## 4. Assignments

### Claude: design and analysis only

| Item | Why Claude |
|---|---|
| DS ROM recovery: field-phase lever and SU-chain fusion; matched-reference checkpoint | Architecture work; drives the DS ROM to beat the matched HBM accelerator in both AR and MTP |
| Qwen DSpark final verdict; atlas, analytical-report and paper write-up | Analysis and academic writing |
| DS q-element closure; DS link/hop closure | Close and subtle |
| Structural redesigns: Qwen core decode; HBM collective endpoint, SU lane and SFU tail, attention tile, SM element | Need new RTL structure; Codex runs their closure loops after Claude posts a designed fix |
| Cross-target analysis, comparisons, energy, priorities; review of Codex results | Judgement |

### Codex: maximum parallelism, one sub-agent per item

Handoff files are in `/tmp/claude-review-20261003/handoff_to_codex_20261004/`; the index is `00_INDEX_AND_DIRECTIVE.md`.

| # | Item | Acceptance |
|---|---|---|
| 0 | **Top priority:** Qwen ROM combined top on STREAM4 with adopted flags; one exact 8K token (36 layers + head), cycles counted | Bit-exact vs GPU golden; cycles recorded |
| 0b | DS S81 native token, time-boxed to 2026-10-05 12:00 PT, then park | Exact native token or exact blocker |
| 1 | DS wavefront controller closure (R11) | SS ≥ 0 / FF ≥ 0 at 1.2 GHz; stage bench exact |
| 2 | DS L1 fused draft head closure (C7k) | Same |
| 3 | DS re-index gather control (kc5); merge closed mdrop | Same |
| 4 | DS window block full screen | Screen passes at 1.2 GHz |
| 5 | Spine power gating: routes, gate-level power, energy recompute | Routed closure; measured residual |
| 6 | HBM R5a expert fetch physical | Placement legal, SS/FF closed, 88/88 exact |
| 7 | Qwen ROM die: slab share → grow slabs → 50-iteration GRT, PDN, IR → STA of worst nets | 0 overflow; IR ≤ 35 mV; nets meet timing |
| 8 | Tape-out: scanned element route, BIST at 1.2 GHz, HBM loader install/timing/reverse, UPF/meso/EM | Per handoff |
| 9 | HBM Qwen-side 1.2 GHz blocks + fmax inventory | SS/FF closed per block |
| 10 | DS S81 full-die physical rerun with the adopted recovery levers | 0 overflow at 50 iterations; IR ≤ 35 mV |
| 11 | Ops: scoreboard regeneration, register hygiene, cleanup, fleet balancing | Scoreboard `--check` 0 failures; no unowned live jobs |

**Rules for every Codex sub-agent:**

- Poll with cheap shell monitors.
- Run the next recipe variant immediately when one misses.
- Self-merge to main.
- Post one result line per hour (numbers or blocker) in `codex_notes`.
- **Escalate** with a `-> CLAUDE <item>` line after 3 failed variants, when an RTL/architecture change is needed, or when exactness fails.

## 5. Major risks

1. **DS ROM AR gap to the matched HBM accelerator.**
   - **Target (owner 2026-10-05):** the DS ROM continues to closure and aims to beat the matched HBM accelerator in both AR and MTP. The comparison is a measured checkpoint for the paper, not a kill switch.
   - Today, against the matched reference (`b39173b46`), the ROM leads on MTP: step 853.6 vs 1,050.6 µs, 4,872.2 vs 3,958.5 tok/s at tau 4.159. It trails on AR: 604.3 vs 474.8 µs, a 129.5 µs gap.
   - The token is latency-bound. Field matvecs are 37% of the AR critical path: serial phases with a fixed cost of 200–260 cycles each, experts swept one after another, no K-split. Serial SU chains are 26%.
   - The field-phase lever (PQ) is exact and worth +20.5% AR (measured on the 1,612.7 tok/s base), but it is rejected until its spine closes SS at 1.2 GHz (−722.8 ps). That spine, the remaining SU-chain fusions and expert concurrency are the levers for the AR gap.
2. **1.2 GHz on baseline blocks across all three targets.** Every rate assumes 1.2 GHz. At today's closing clocks the DS HBM AR falls to 1,656.3 tok/s. Open baseline blocks:
   - Qwen core decode;
   - Qwen port/scale slab;
   - Qwen landing merge;
   - HBM collective endpoint, SU lane and SFU, attention tile;
   - DS re-index gather control;
   - DS wavefront controller;
   - DS fused head;
   - DS q-element.
3. **Physical regression from recovery levers.** The S81 die passed physical feasibility before the head, draft-placement (+52 dies), window, field and SU changes, on a netlist with connectivity holes (die-top lint `7ccef3810`). A full-die rerun on the wired r8 netlist is required (Codex item 10).
4. **Routability of dense blocks.**
   - Seen in the Qwen slab pins, the DS scanned element, the R5a macro channels and the earlier near-HBM hub.
   - Expect more frame or pin-plan iterations than logic iterations.
5. **Integration.**
   - No native end-to-end S81 token yet.
   - The Qwen combined top still needs STREAM4 and flags on.
   - Component-exact results are composed rather than run as one design.
6. **Tape-out gaps.** No UPF; meso FIFOs and forwarded links not instantiated in die tops; no pad/ESD/package PHY; no die-level EM; the HBM accelerator has no die floorplan.
7. **Process.**
   - Claude rate limits (four stops in one day, one weekly limit).
   - EPYC CPU saturation (mitigated by ot-epyc2).
   - Coordination misses between agents (mitigated by the `-> CLAUDE` scan and this plan).

## 6. Order of work and expected dates

Ranges reflect today's experience that closure needs several iterations.

| Milestone | Owner | Expected |
|---|---|---|
| Qwen DSpark verdict file; atlas/report updated | Claude | 2026-10-05 |
| DS field-phase + SU-chain lever results; matched-reference checkpoint (measured, for the paper) | Claude | about 2026-10-06 |
| Qwen ROM integrated 8K token on STREAM4 (Codex) | Codex | 2026-10-06/07 |
| Qwen ROM closure (core decode, slab, landing merge, die rerun) | Claude + Codex | 2026-10-07/08 |
| HBM accelerator 1.2 GHz datapath closure (both models) | Claude designs, Codex closes | 2026-10-08/09 |
| DS ROM closure: blocks + S81 die rerun + native token, targeting AR and MTP ahead of the matched HBM accelerator | Claude + Codex | 2026-10-08/09 |

## 7. Where to look

- **Measured scoreboard:** `results/arch/measured_scoreboard/README.md`
- **External figures:** `results/external/registry.json`
- **Experiment register:** `/home/ubuntu/opentallas-monitor/experiments.json` (protocol: `docs/EXPERIMENT_REGISTER.md`)
- **Handoffs to Codex:** `/tmp/claude-review-20261003/handoff_to_codex_20261004/`
- **Shared notes:** `/tmp/claude-review-20261003/codex_notes.txt`
- **Fleet:** `results/arch/fleet_epyc2_20261004/README.md`; monitor <https://rtx-pro-files.01.me/fleet/>
