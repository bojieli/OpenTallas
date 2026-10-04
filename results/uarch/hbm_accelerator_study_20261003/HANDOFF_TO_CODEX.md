# Handoff to Codex: the HBM inference accelerator (second proposed design), 2026-10-03

- From: Claude, branch `claude/hbm-accelerator-study-20261003`.
- Status: MODEL ONLY. Numbers are in [STUDY.md](STUDY.md) and `ladder.json`; replay with `ladder_model.py` (see [REPLAY.md](REPLAY.md)).
- Rungs marked **ESTIMATE** carry transferred or assumed constants. Each has an explicit price-first task (section 4).

## 1. Goals and positioning (user decision, 2026-10-03)

**What changes:**
- The HBM design becomes our **second proposed design**: an HBM inference accelerator, not a GPU, built with our system improvements.
- The GPU-organised comparator stays as the **ablation**, "HBM accelerator without our improvements". Its records are not edited.
- AGENTS.md rule 3 is being changed by the user. Until then, label every accelerator-only feature "accelerator (ours)" and keep the ablation rows GPU-real.

**Targets (model, per user, batch 1):**

| Model | Context | Ablation | Accelerator target |
|---|---|---|---|
| DS V4.1 | 1M, AR | 2,262 | **≥ 3,000** |
| DS V4.1 | 1M, DSpark γ5 τ 3.649 | 4,848 | **≥ 6,000** |
| DS V4.1 | 200K | within 0.2% of 1M | within 0.2% of 1M |
| Qwen3-8B | 8K | 881 AR / 2,671 DFlash | 1,051 AR / 3,356 DFlash on the same 2-die/8-stack silicon; 2,391 / 7,493 at iso total silicon with ROM option C |

**Positioning to verify, not assume:**
- DS: the HBM accelerator should beat the ROM array per user and per mm².
- Qwen dense: ROM should win on AR and on energy (0.115–0.148 J against 0.27–0.85 J).
- **Open risk:** with DFlash, the HBM accelerator beats the ROM AR-only target on Qwen. Report this honestly.

**GPU baselines** (same workload, labelled tier): see STUDY.md. The DS GPU row must use the 38→8 scanning-layer fix (`32d865831`): 282.4 / 547.8.

## 2. Priced ladder (DS 1M, firm rungs)

| Step | µs saved (AR) | Result (tok/s) |
|---|---:|---:|
| Ablation as recorded | – | 2,261.7 |
| R0c honest service term | −14.9 | 2,188 |
| R1b tx-count completion | +8.9 | |
| R2 direct 2-level links | +70.1 | |
| R3a cut-through | +17.9 | |
| R3b TMEM epilogue | +6.1 | |
| R4b per-stack scorers | +3.4 | |
| R5a refresh-aware fetch | +13.5 | |
| R5b shared-expert-first | +5.6 | |
| R6a P select units (MTP only) | +14.0 on verify | |
| **Total** | | **3,015 AR / 6,001 MTP** |

- R7a (serial chain at 1.091 GHz, conditional) would give 3,144 / 6,293.
- Full table: STUDY.md.

## 3. Workstreams (all start in parallel; each is opt-in, off by default, and leaves pinned files byte-identical)

Every workstream has the same three gate types:
- **Exactness gate:** bit-exact against the golden, through `tools/w19_hbm_tp96_isa.py` (per layer, plus head token 21946 at 1M) or the Qwen canonical launcher.
- **Measurement gate:** measured cycles in the system context, compared with the price in this study. Adopt only if the gain is at least 1% per user.
- **Physical gate:** SS setup and FF hold at 1.2 GHz, 60/25 ps, in context. Run P&R only after the exactness and measurement gates pass (FLEET_AND_FLOW.md).

### HA0: model integration (do first; does not block the others)

- **Scope:**
  - Add `hbm_accel_rows()` with an `--hbm-accel` flag to `tools/uarch_model.py`, importing this study's rung table.
  - Apply `v41_hbm_service_term_20261003/uarch_model_service_term.patch` as a labelled row.
  - Add a GPU-faithful R0 row: grid sync at 1.43 µs per boundary, giving 1,099 tok/s. The current ablation's 62-cycle barrier is not GPU-real; label it.
  - Add a DRAM mm²-per-stack constant (sourced; currently ASSUMED at 1,000), iso-power rows, an H100 tier-2 row, and the Qwen3.8-27B config under `configs/models/candidates/`.
- **Reuse:** HBM_W19 and v41_hbm_sweep (`consolidation.json`); `ladder_model.py`.
- **Acceptance:** reproduces `ladder.json` within 0.1%; defaults unchanged.
- **Effort:** about 1 day. **Host:** local.

### HA1: dataflow completion (R1b)

- **Scope:** replace the barrier's release broadcast with per-SM tx-count arrival counters, mbarrier-style.
- **Files:** new `rtl/gpu/ot_gpu_txcount_barrier.sv`, plus a mode in `ot_gpu_full_sm_service.sv`.
- **Reuse:**
  - `tb_gpu_barrier`
  - `results/rtl/gpu_supply_barrier.json`
  - W4 RF-ACK identity (`6279cbb23`)
  - W6 fence (`f7386a417`)
- **Measurement gate:** boundary ≤ 47 cycles (now 78).
- **Physical gate:** arrival tree on `results/floorplan/hbm_gpu/v41_hbm_die.json` distances, SS/FF.
- **Effort:** 2–3 days. **Host:** agidock128.

### HA2: direct die-to-die topology and collective endpoint (R2, the largest rung)

- **Scope:** a 96-rank, 2-level topology: groups of 16 dies fully connected, plus 5 global links per die, for about 20 narrow links per die.
- **Reuse:**
  - `rtl/rom/collectives/ot_rom_hcoll_die.sv` and the C1/C5hc fits (`4ec2eef0e`)
  - `rtl/link/ot_link_*`
  - `ot_link_nvls_switch.sv` (W15) as the ablation reference
  - `ot_coll_topk_merge.sv`
  - `rtl/gpu_sys/coll_*` (`759f7cdcf`)
- **Measurement gate (Verilator, wire stages included):**
  - 96-rank gather fixed latency ≤ 550 ns and all-reduce ≤ 650 ns; the W15 references are 777 and 824 ns.
  - Slopes measured.
  - The 96×512 top-k merge measured.
- **Exactness gate:** fixed-order trees, deterministic; csum plus the executor.
- **Price first:**
  - Port count, lanes and SerDes area/power per die. Target: within the current 18 mm² fabric SerDes and 33 W per die of link static power.
  - The light-FEC 130 ns link must be cited or measured.
  - Optimistic sensitivity: a switch with in-switch reduction (ASSUMED 400 ns), worth about +10%.
- **Effort:** 1–2 weeks. **Host:** agidock128 (benches); EPYC for the 96-rank build if it exceeds 20 GB.

### HA3: cut-through collectives and epilogue fusion (R3a, R3b)

- **Scope:**
  - Port the Qwen async collective pattern to the HBM SM→collective endpoint. Source: `rtl/rom/ot_qwen_tp_seq_async_w12.sv` (`d79a2089c`); fused + cut-through measured −278 cycles per layer.
  - Build the TMEM-style epilogue from W13b `f984ba8d` (`hbm_sm_epilogue_study.json`).
- **Exactness gate:**
  - The two FAILED Qwen fused-epilogue gates (non-finite, wide overflow) must be resolved, not overwritten.
  - Golden rounding points kept.
- **Price first:** R3a is transferred from Qwen at 67 ns per collective. Measure it on the HBM endpoint.
- **Effort:** 1 week. **Host:** agidock128.

### HA4: HBM controller service (R5a, R4b)

- **Scope:**
  - Adopt `ot_hbm_r14_stream_{pc,stack}.sv` (`52ce3e9c1`; 0.958 TB/s per stack, REFpb + notice) on the routed-expert fetch path: `rtl/gpu/ot_gpu_expert_fetch.sv` (`c52ae6d7f`).
  - Add per-stack index scorers and a top-k chase (model `723243a4a`).
- **Measurement gate:** with refresh live, first access after top-6 ≤ 140 ns; the central figure is now 469.5 ns.
- **Physical gate:** the stream controller fails 1.2 GHz SS by −4.7 ps (closes at 976.6 MHz). Either close it at 1.2 GHz or price the CK/2 service.
- **Fix:** the known `commit_r` undriven defect (`ot_hbm_causal_command_provider.sv:20`).
- **Effort:** 1 week. **Host:** pve1 (medium-memory sims) and agidock128 (synth/STA).

### HA5: program and compiler changes (R5b, R6a, γ)

- **Scope:**
  - In `tools/w19_hbm_tp96_isa.py`, issue the shared expert (slot 6) before the routed slots; the sum order is unchanged.
  - Use P parallel select units in verify: replicate `ot_coll_topk_merge`.
  - Re-run `tools/w19_hbm_token_compose.py` and `tools/v41_hbm_speculation_methods.py` (`d2aff19ef`), with a γ sweep.
- **Exactness gate:** the executor stays bit-exact per layer and at head token 21946.
- **Price first:** the R5b hide window is an ESTIMATE (10.6 µs). Measure the slot-6 SM time.
- **Price first, collective-count reduction:** 6 collectives per regular layer. Find exact merges or replications; every 40 collectives removed is about 20 µs.
- **Effort:** 3–5 days. **Host:** local / agidock128.

### HA6: serial-chain clock (R7a, conditional) and the clock risk

- **Scope:**
  - Serial domain at 1.091 GHz LAT-3: pipelined FP32 add with ADDER_MAP off.
  - Fix the 2-clock ratio FIFO: `ot_chip_v41_ratio_fifo_2clk` fails SS by −75.6 ps.
- **Shared with the ROM lane:** coordinate, do not duplicate.
- **Risk row:** if no 0.9 GHz domain is realised, local time grows by about 1.6× (about −10% AR). Report this as a negative rung.
- **Effort:** 1 week. **Host:** agidock128 / pve1.

### HA7: speculation (R6) and router-predicted prefetch

- **Scope:** recompose DSpark on the accelerator. Measure router-predicted expert prefetch recall on **local GPU only**.
- **Data:** the hidden-state predictor needs inference; the existing router traces are `/tmp/claude-review-20261003/v41spec/router_full.pt`.
- **Facts to price against:**
  - Previous-token reuse is only 1.6 of 6 experts (U(2) = 10.4).
  - Adopt only if AR or verify gains are at least 1%.
- **Also:** the R8b union stream at 2 stacks per die (ESTIMATED at about −4% MTP). Measure it.
- **Host:** local RTX PRO 6000 for any inference; CPU hosts for composition only.

### HA8: the Qwen3-8B HBM accelerator

- **Scope:**
  - (a) Same-silicon point: 2 dies, 8 stacks, 842 MiB SRAM holding the lm_head first, streaming controller.
  - (b) Iso-total-silicon point: 4 dies TP-4, 16 stacks, about 1.7 GiB SRAM.
  - (c) DFlash b16 on the 16 MMA columns: `ot_gpu_sm` with 16 columns already built.
- **Exactness vehicle:** Codex's canonical Qwen launcher.
  - Reuse: `tools/gpu_sys/run_canonical_qwen.py`; W2/NC6 (`d347da59b`), W4, W6, rank bank `82847f817`, `b7de919b0`.
  - First reach a full token.
- **Price first:** SRAM macro density and read power at the real macro; HBM stream efficiency between layers (back-to-back average 0.842 TB/s, against 0.958 worst-layer in isolation).
- **Effort:** 2 weeks (critical path: the full token). **Host:** agidock128 (Verilator layer jobs, about 1.5 GB each).

### HA9: physical (after HA2 and HA8 sizing)

- **Scope:** accelerator die floorplans. DS: 340.5 mm² right-sized die plus about 20 link ports. Qwen: SRAM tiles. Hierarchical abstracts only; no flat full-die runs.
- **Host:** EPYC (`admit.sh`). ORFS runs use NUM_CORES 16–24.

### HA10: fairness and economics

- **Scope:**
  - Rows at iso power and iso total silicon, with HBM DRAM counted.
  - J/token at batch 1 and saturated.
  - ROM vs HBM accelerator per model class.
  - Sync the stale 2,920 in `docs/MICROARCH_MODEL.md`, then regenerate the census and run `make check-figures`.
- **Host:** local.

## 4. Price-first tasks (rungs not yet priced)

- Collective-count reduction (HA5).
- Router-predicted prefetch recall (HA7).
- Die count and stacks per die at iso power (HA0; the sweep is already in `consolidation.json` `hbm.v41_sweep`).
- Port and SerDes sizing (HA2).
- MTP penalty at 2 stacks per die (HA7).
- Qwen3.8-27B ROM sizing (HA0/HA10).

## 5. Dependencies and order

- **Start now, in parallel:** HA0–HA8. None blocks another's RTL.
- **Final composition:**
  - HA7's final composition needs HA2, HA3, HA4 and HA5 measurements.
  - HA9 needs HA2 port counts and HA8 SRAM sizing.
  - HA10 needs HA0.
- **Critical path:** HA2 (largest rung) and HA8's full Qwen token.
- **Order:** launch HA2 and HA8 first; HA1, HA3, HA4, HA5 and HA6 are short and fill the hosts.

## 6. What NOT to do

- Do not edit the ablation records or pinned files.
- Do not overwrite failed verdicts.
- No ceremony: no new preflight or attestation layers without a measurement.
- No model inference on CPU hosts.
- Do not run P&R before the exactness and measurement gates pass, and no flat full-die runs.
- Do not relax clock constraints.
- Do not adopt a rung below 1%. R4b alone is 0.96%: adopt it only if measured above the gate.
- Never `git add -A`.
- Do not merge to main untested; trial-merge in a worktree first.

## 7. Reporting format

Report one JSON record per run in `results/rtl/hbm_accel_<ws>_<date>/`. Each record carries:
- schema, source commit, input sha256
- exact verdict (cases / mismatches)
- measured cycles and ns
- the price from this study, and the delta between measured and priced
- SS/FF WNS and area
- adopt / reject

Also add a one-line ledger row to the study (rung, measured µs, tok/s after). Report each run as: run id, host, numbers.
