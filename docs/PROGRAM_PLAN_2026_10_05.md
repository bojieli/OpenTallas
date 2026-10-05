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
- Acceptance (tau) and GPU baselines come from published third-party figures (`results/external/registry.json`).
- MTP is required where it pays.
- Mandatory baseline blocks must close: only optional levers face the ≥ 1% reject rule.
- Nothing heavy on localhost.
- Every live job has an owner in the experiment register.

## 2. Where each target stands

| Target | Headline (measured) | Exactness | Physical | Status |
|---|---|---|---|---|
| Qwen3-8B ROM, 8K | AR on STREAM4: **6,169.7 tok/s** (5,974.3 wire-bound); 2.99x the one-stack path (`results/rtl/qwen_rom_kv_fullbw_20261004/`) | All 4 dies and token K/V bit-exact vs GPU golden | Die 811.8 mm²; global route **closed** (b3r16B40, 0 overflow, `f1df64409`); IR 20–26 mV | Core decode −217 ps; port/scale slab share open; landing merge −0.75 ns |
| DeepSeek-V4.1 ROM, 1M | **1,612.7 AR / 4,462.1 MTP** (all measured; head lever adopted `1c4e785ee`, window bound `42cf43125`) | Every term bit-exact; 3 interaction bugs found and fixed (`952159dfa`, `be155754b`); no native end-to-end S81 token yet | S81 layer and head dies passed at `21fcf6469` (0 overflow, IR 28.6–32.2 mV), **before** the recovery levers | Recovery in progress; several blocks still closing |
| HBM accelerator, DS 1M | **2,173.7 AR / 4,377.9 MTP** (fully measured `7dfe62676`, notice default) | Exact | Control loops closed (bulk copy, KV lifecycle `7ce508488`, SECDED fence `b5f1dcdf6`) | Datapath short of 1.2 GHz: collective endpoint −329 ps, SU lane −4.8/−46 ps, SFU tail −113/−167 ps, attention tile about 881 MHz |
| HBM accelerator, Qwen 8K | 2,154–2,220 AR; DSpark about 5,055 (TP4, `2f4a6af49`) | Exact (TP2 and TP4 vs GPU golden) | Not closed: Qwen-side core, collective and lane blocks open | Handed to Codex |

**Comparisons at equal silicon, measured:**

- **Qwen:** the ROM (AR, STREAM4) is about 2.7x the HBM accelerator's AR.
- **DeepSeek:** the ROM is 0.74x the HBM accelerator on AR and **1.02x on MTP**.
- **Energy** (`0bc89506e`):
  - Qwen ROM leads (0.165 vs 0.761 J/token, model power).
  - DS HBM leads DS ROM at batch 1 (5.81 vs 6.79 J/token) until spine gating is measured.

## 3. Decisions already taken

- **Qwen ROM operating mode is plain decoding (AR) at 8K.** This is conditional on `results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json`.
  - DSpark on the compute-balanced ROM measured 0.763x AR (free-draft bound 0.969x): the ROM's read rate equals its MAC rate, so a 4-position verify layer costs 3.26x an AR layer.
  - DSpark stays built and exact but off.
  - MTP stays required and pays on the DS ROM (2.75x) and the HBM accelerator (2.28x).
  - Principle: speculation pays only when the dominant per-token cost is shared across the verified positions.
- **Near-HBM attention dropped** (`c8d7ab368`); the KV path is STREAM4. The old HBM_STREAM controller is retired.
- **DS ROM batched draft head (L2, NV5) rejected.** It is wire-bound: routed −674 ps.
- **Rejected optional levers** (recorded with measurements): HA3 cut-through, async collective (SB_PIPE 1–4), index row layout, 2,048-lane SU, edge-gap floorplan, Option A slab layering.
- **Fleet:** ot-epyc2 added as a twin of ot-epyc1tb (`4447740f7`); `admit.sh` runs on all four remote hosts.

## 4. Assignments

### Claude: design and analysis only

| Item | Why Claude |
|---|---|
| DS ROM recovery: field-phase lever and SU-chain fusion; DS decision gate | Architecture work; sets whether the DS ROM beats the HBM accelerator |
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

1. **DS ROM value proposition.**
   - Fully measured, it trails the HBM accelerator on AR (0.74x) and only ties on MTP (1.02x).
   - The token is latency-bound. Field matvecs are 37% of the AR critical path: serial phases with a fixed cost of 200–260 cycles each, experts swept one after another, no K-split. Serial SU chains are 26%.
   - The field-phase and SU-chain levers decide whether it wins.
   - **Decision gate (about 2026-10-06):** if it is still below the HBM accelerator after those levers land, the owner decides whether the DS ROM continues, is redirected (energy or capacity), or is narrowed.
2. **1.2 GHz on baseline blocks across all three targets.** Every rate assumes 1.2 GHz. At today's closing clocks the DS HBM AR falls to about 1,646 tok/s. Open baseline blocks:
   - Qwen core decode;
   - Qwen port/scale slab;
   - Qwen landing merge;
   - HBM collective endpoint, SU lane and SFU, attention tile;
   - DS re-index gather control;
   - DS wavefront controller;
   - DS fused head;
   - DS q-element.
3. **Physical regression from recovery levers.** The S81 die passed before the head, draft-placement (+52 dies), window, field and SU changes. A full-die rerun is required (Codex item 10).
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
| DS field-phase + SU-chain lever results; DS decision gate | Claude | about 2026-10-06 |
| Qwen ROM integrated 8K token on STREAM4 (Codex) | Codex | 2026-10-06/07 |
| Qwen ROM closure (core decode, slab, landing merge, die rerun) | Claude + Codex | 2026-10-07/08 |
| HBM accelerator 1.2 GHz datapath closure (both models) | Claude designs, Codex closes | 2026-10-08/09 |
| DS ROM closure (if continued): blocks + S81 die rerun + native token | Claude + Codex | 2026-10-08/09 |

## 7. Where to look

- **Measured scoreboard:** `results/arch/measured_scoreboard/README.md`
- **External figures:** `results/external/registry.json`
- **Experiment register:** `/home/ubuntu/opentallas-monitor/experiments.json` (protocol: `docs/EXPERIMENT_REGISTER.md`)
- **Handoffs to Codex:** `/tmp/claude-review-20261003/handoff_to_codex_20261004/`
- **Shared notes:** `/tmp/claude-review-20261003/codex_notes.txt`
- **Fleet:** `results/arch/fleet_epyc2_20261004/README.md`; monitor <https://rtx-pro-files.01.me/fleet/>
