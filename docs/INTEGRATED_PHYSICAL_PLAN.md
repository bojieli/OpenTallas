# Integrated design plan: close the modeled single-user path (revised 2026-10-01)

Integration owner: Codex. This checkpoint is based on main `bb01a425a`, the pin-only follow-up `7d4727e59`, and the bounded W11 lane evidence `518363bd1`. The binding method is [AGENTS.md](../AGENTS.md); the architecture is Atlas Table 5-2 ([ARCHITECTURE_ATLAS.html](ARCHITECTURE_ATLAS.html)), and the unified model is [MICROARCH_MODEL.md](MICROARCH_MODEL.md). [TASKS.md](../TASKS.md) tracks stream ownership.

**Objective order:** minimum single-user decode latency first; maximum independent-request batching throughput second. Exact arithmetic, golden rounding points and reduction order are mandatory. There are three active tracks: Qwen ROM, DeepSeek ROM, and HBM comparators for both models. The HBM track contains two model-specific designs; it does not replace either ROM track.

## Build and adoption method

Size every block and its composed token latency in `tools/uarch_model.py` before RTL or place and route. Floorplan the modeled array, harden one complete element, then replicate. Model coverage is not physical completion: final abstracts, composed routing, clock closure and actual-element power remain acceptance gates.

- Streaming target: 1.2 GHz at SS. DeepSeek's serial chain target is 0.9 GHz. Both are targets for in-context closure, not closed product clocks.
- Sign-off: SS setup and FF hold, with 60 ps setup and 25 ps hold uncertainty. TT evidence is pathfinding only. Memory macros use their own SS clock-to-q.
- Preserve golden arithmetic; new levers remain opt-in and off by default until exactness, routing, contextual SS/FF and measured performance gates pass. A slower or non-closing measured lever is rejected rather than tuned. The model must price at least a 1% per-user gain before adoption.
- Lane-local fusion and dataflow levels 1–5 are the authorized design direction. An estimate or a gain on a reduced vehicle is not product qualification. Norm-after-matvec needs the unchanged QC-NAM quality and stability PASS.
- HBM comparators retain GPU organisation and only GPU-real mechanisms. ROM-specific weight-bank novelties do not transfer to HBM.
- Reuse live jobs and coordinate through existing host manifests. Long jobs retain clean source pins; edits and integration use isolated worktrees. Stage explicit paths and retain failed evidence.

## Current track priorities

| Track | Qualified evidence | Blockers and next acceptance |
|---|---|---|
| Qwen ROM — W12b | The historical TP-2 full-token receipt has exact token/state and source/binary/vector checks. TP-4 receipts establish partial checkpoint agreement, not a completed product token. [Receipt](../results/rtl/qwen_rom_w12_runtime/terminal_20261001/verification.json). | Finish the existing TP-4 token and collective-latency work; close tile, spine and die power at the unchanged sign-off. Feed measured body and collective timing separately into the model. The ROM remains autoregressive option C. |
| DeepSeek ROM — W10b/W11/W17/W18b | Full-shape ISA and historical field-composition evidence retain their original scope. Runtime admission and retry checks qualify prerequisites. [W17 recovery](../results/rtl/w17_recovery_89eace_validation_20261001.json). | Resolve the preserved local die timeout with a bounded diagnostic; establish integrated-source field/CKV exactness before a full die rebuild. Finish existing element and K-arbiter routes, then require actual final abstracts before the die rebase. [Physical status](../results/physical_abi3/asap7/chip/w10_w18_recovery_20261001/physical_status.json). |
| HBM for Qwen and DeepSeek — W13b/W15b/W19 and Qwen helper | DeepSeek's bounded fetch/SM and finite-sector payload gates, historical fixtures and remote replays are qualified only at the recorded scope. Historical arithmetic compatibility is distinct from a fresh model preflight. [Production continuation](../results/rtl/w19_production_continuation_20261001.json). | Complete loader/swizzle and connected router/multi-SM scheduling, realistic HBM contention, full-rank AR/MTP tokens and contextual SM/link closure. Qwen HBM remains a separate connected comparator deliverable. No transport gate establishes a full-token rate or hardware adoption. |

The highest open element closure and token-path blockers within these tracks take precedence over additional feature streams. Outputs must compose through the unified model.

## Shared gates and rejected work

**W11 fusion has no product qualification.** The N64/M16 KR40 lane configuration is exact at its tested batch scope but measured slower; reject that configuration without tuning or restart. The N16/M8 lane gain remains unadopted. [Bounded lane record](../results/rtl/w11_lane_terminal_20261001/summary.json). The earlier reduced wired-die gain comes from a different historical vehicle with overall FAIL, so it is neither a contradiction nor a full-product timing correction. Keep its reduced timing-model discrepancy scoped to that vehicle. [Calibration and original failure](../results/quality/qcnam_w16_recovery_20261001/recovery.json).

**Physical closure remains contextual.** The recovered softplus terminal record did not meet its constraint; separate FF sign-off is not established. [W11 terminal handoff](../results/rtl/w11_terminal_recovery_20261001/handoff.json). W10's rejected frontend and failed q-pair routes stay rejected. BF16 c8 and root K-arbiter route observations are not extracted final sign-off. The rejected KSREG region also retains power-connectivity and corner failures. [W10/W18 status](../results/physical_abi3/asap7/chip/w10_w18_recovery_20261001/physical_status.json).

**The die rebase is blocked on final elements.** Historical tile dimensions and the old-element IR sensitivity cannot stand in for final q/BF16 LEF, corner ETMs, source pins and measured latency/power. Require same-source exactness, hub routing-layer acceptance, root/region closure, zero route overflow and actual-element IR. Current owner allocation is a modeled placement, not a completed die.

**QC-NAM remains pending.** Core completed, while the generation and MMLU lanes remain live at this checkpoint; long-context scoring follows the existing lane script. There is no finalized full-model verdict. Stability thresholds were tightened after two three-layer smoke runs and before full-model results, not before all observations. Preserve the original smoke stability FAIL and `adopt=false`. [Registration and fingerprint review](../results/quality/qcnam_w16_recovery_20261001/integration_review.json). The readiness watcher launches no evaluation; it invokes the unchanged pinned finalizer only after every required lane and paired metric validates. Preserve either final PASS or FAIL; a final quality record alone does not waive physical or performance adoption gates.

**W15 and FA remain scope-bound.** Historical source binding, arithmetic tests and replay reconciliation do not certify current-source physical timing. Keep SRAM provenance failures and stopped routes intact. Fusion estimates remain estimates until RTL, routing and corner acceptance pass.

## Model calibration and headline policy

The current generator-pin refresh changes no model rates or headline values. Its proof excludes only the new uncalled W19 transport-sizing function; all other computational model AST is identical. [Pin-only audit](../results/quality/w16_parent_pin_audit_20261001.json).

Preserve older historical generator and input pins where the source has materially drifted. A reduced trace does not justify a raw multiplier on the full product. Price actual token-body, collective, memory-service and serial-network delays on matched configurations, without double-counting measurements already composed by the model.

No current product-rate headline is published by this update. The Atlas abstract, Table 2-1 and earlier evaluation rates are explicitly historical checkpoints until full-product calibration and sign-off justify a joint restatement. Single-user rate stays primary; equal-cost throughput, energy and cost are secondary comparisons. ISA exactness, bounded transport receipts and admission tests do not establish full-token RTL timing.

## Retired work and host coordination

Legacy worktrees, superseded builds and checkpoints are retired only after exact-boundary process/manifest checks and preservation of committed evidence and unique dirty changes. Retiring storage is not a passed gate. The clean W16b checkout was redundant because its model/record content was already integrated; its retirement does not trigger a second model run. The dirty QC development checkout was archived before retirement; the clean QC run pin and current outputs remain protected.

[Committed retirement audit](../results/maintenance/local_disk_recovery_20261001/summary.json) and [owner coordination](../results/maintenance/local_disk_recovery_20261001/owner_coordination.json) distinguish retired storage, live sources and held ambiguous files. Existing queue manifests coordinate PVE, AGIdock and local jobs. Preserve the QC watcher source until it exits. Do not duplicate an evaluation or physical run just because its historical edit checkout was retired.

## Exit criteria

Each model/design needs a full-shape bit-exact RTL token, measured composed cycles carried by the model, and complete contextual SS/FF physical records at the unchanged uncertainty policy. ROM die acceptance also needs actual-element route and power evidence; HBM acceptance needs connected production service under realistic contention. QC-NAM adoption additionally requires the unchanged full quality and stability verdict. Only then restate calibrated rates together.
