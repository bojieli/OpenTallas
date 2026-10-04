# Current work handoff — 2026-10-03

This is the continuation handoff for the parent integration agent. Repository and live-process observations were taken at approximately 00:58 UTC on 2026-10-03. The source baseline is main/origin/main `7c3fb3e43479fda6caf454c7f76b294b5fba6caa`. This document is a snapshot; inspect processes and workers again before launching, deleting or integrating anything. Preparation of this handoff does **not** stop ongoing jobs or cancel the project.

## Start here

Read [AGENTS.md](../AGENTS.md), [INTEGRATED_PHYSICAL_PLAN.md](INTEGRATED_PHYSICAL_PLAN.md), [TASKS.md](../TASKS.md), [MICROARCH_MODEL.md](MICROARCH_MODEL.md), and the architecture statement in Atlas Table 5-2 in [ARCHITECTURE_ATLAS.html](ARCHITECTURE_ATLAS.html). This handoff supplements them with the latest integration state, specific evidence scopes, worktrees and recovery instructions. Some older plan paragraphs describe earlier blockers; use the source-pinned records and the newer statuses below to resolve those differences.

The project is a reproducible architecture research implementation under ASAP7, not a tapeout. It still requires complete functional execution, connected RTL, finite memory service and contextual physical feasibility. The four combinations are Qwen3-8B ROM, Qwen3-8B HBM, DeepSeek-V4.1 ROM, and DeepSeek-V4.1 HBM. The owner calls these three tracks because the two HBM comparators share an established GPU organisation.

**The project is not complete.** `python3 tools/current_final_number_readiness.py --check` passes its consistency check, but reports G0 through G5 blocked for every combination and `terminal_ready=False`. A passing figure or readiness consistency check is not a passing final qualification verdict. The retained Qwen TP4 numerical result is explicitly recognised as passing at its captured scope.

First continuation actions, in priority order:

1. Preserve the live Qwen L0 observation and the surviving PVE1 physical process. Read their outputs; do not restart them to change limits or settings.
2. Review Dewey's installed HBM calendar successor and Kepler's complete dual-runtime resource projection. Finish the missing production execution bridge and launch the DeepSeek numerical continuation once its actual combined inventory fits.
3. Complete one coordinated Qwen per-word readiness calendar after the rejected extra-credit candidate. Bind it to actual source observations rather than independently sweeping credits, dispatch and geometry.
4. Complete the DeepSeek ROM fixed-graph relay-placement repair and compose literal clock/reset/power/routes with the finite service calendar. This is the reticle/physical critical path.
5. Continue actual numerical reference coverage and native execution independently of physical work, without repeating already checked prefixes.
6. Integrate coherent reviewed milestones into main and push. Do not turn every small step into a commit or claim that a software reference is a hardware execution result.

## Owner decisions that must survive the handoff

Single-user decoding latency is the primary objective. Independent-request batching is secondary. DeepSeek's target is more than the requested accepted-token rate **after MTP**, not an AR-only claim. No qualified third-party median agentic acceptance assumption has yet been bound to the performance claim; historical acceptance values are sensitivities, not adopted workload facts.

Keep the current compute-beside-ROM design. HBM comparators use SM-like matrix units, register files/shared memory, L2 and shoreline HBM controllers. Do not copy ROM-specific novelties into the HBM comparison. A larger die array is allowed only with coordinated storage, compute, communication and single-user latency pricing. The DeepSeek die outline remains within the owner's fixed reticle envelope; changing ROM depth alone does not remove the weight area.

Exact golden rounding points and reduction order remain mandatory. ROM ECC has been removed by owner decision, including configuration ROM ECC and ECC-only sidecars. This does not remove mutable SRAM/HBM/link/control protection, transaction identity, descriptor validity or address bounds. Do not quietly substitute mandatory parity/CRC for ROM ECC. Preserve earlier ECC evidence as history.

Streaming and serial-chain clocks and SS/FF uncertainty are those in AGENTS.md. TT is pathfinding only. Never relax constraints to manufacture closure. Model a block and its composed latency before RTL or P&R. Optional levels 1–5 remain default-off until exactness, model gain, measured RTL gain and in-context closure pass. Reject slower/non-closing optional candidates rather than using the baseline budget to tune them. Mandatory baseline correctness still needs repair.

QC-NAM is **complete and rejected on numerical-stability FAIL**. Do not reopen norm-after-matvec or count its performance saving. The final authority is [the quality verdict](../results/quality/deepseek_v41_flash_norm_after_matvec.json).

The retained Qwen ROM TP4 position-zero token is sufficient for the immediate numerical milestone. Do not launch another decode position. The current L0 observation is a source-lifetime audit, not a second full-token campaign.

The owner forbids arbitrary wall-time, CPU-time, file-size and address-space limits on costly builds. Use measured fleet headroom, capacity reservations and free-space monitoring; preserve incremental outputs and failure receipts. A progressing pinned job must not be restarted merely to change its resource settings.

The later fleet decision supersedes the older all-host default: new work may use local, PVE1 and the large VM. **PVE2 and PVE3 are drain-only.** No new tasks there. The original six AGIdock VMs were retired; do not recreate them. The current large VM is a separate active resource. Delete only demonstrably retired worktrees/checkpoints after preserving unique source changes and checking live use.

## Repository and integration state

Main and origin/main were both at the baseline above. The latest reviewed milestone includes DeepSeek layer-one numerical reference extensions, independent replay of the rejected Qwen credit candidate, and PVE1 live-stage retention/SDC-writer failure evidence. The parent clean review tree is `/tmp/opentallas-parent-compact-v3-review-20261003`, detached at the same baseline.

Main contains unrelated untracked files that must not be staged, deleted or reformatted as part of this handoff: `docs/ARCHITECTURE_ATLAS_FEASIBILITY_REVIEW_2026_09_27.md`, `node_modules/`, `package.json`, and `package-lock.json`.

Parent review receipts are under `results/uarch/native_software_parent_intake_20261002/`. Recent authorities include:

- `DS_layer1_reference_parent_review.json` and `DS_layer1_reference_parent_tests.log`.
- `Qwen_credit17_rejection_parent_review.json` and `Qwen_credit17_rejection_parent_tests.log`.
- `PVE1_current_stage_retention_parent_review.json`.
- `DS_R55_immutable_scope_parent_tests.log`.

Use explicit paths when staging. Do not run `git add -A`. A worker commit's ancestry may include old or unrelated material; compare exact paths and dependencies before cherry-picking. Quote Git pathspec globs. A previous unquoted glob expanded only existing files and incorrectly appeared to prove all helper files identical; the missing helper dependency was then found and integrated. Keep that lesson rather than repeating it.

After editing docs, regenerate `results/abi3/prose_figure_coverage.json`, update its two untriaged annotations in `docs/EVIDENCE_LEDGER.md` and `docs/UNIFIED_EXECUTION_CHECKLIST.md`, and run `make check-figures`. Passing this command establishes record consistency, not final performance qualification.

## Evidence summary across the four combinations

| Combination | Strong retained evidence | Remaining qualification boundary |
|---|---|---|
| Qwen ROM | Captured TP4 full token, all layers and head, exact rank checkpoints and final output. | Current source-owned memory lifetimes, credit calendar, payload/PHY bandwidth, loaded capture/clock/routes, same-configuration calibrated rate. |
| DeepSeek ROM | Functional/ISA evidence, exact component paths, substantial symbolic/physical inventory and finite-service work. | Original connected L0 has no final exact DONE; actual source-owned execution, relay/clock/reset/PG/routing composition, full configuration feasibility and calibrated token. |
| Qwen HBM | Full native numerical program and separate actual KV lifecycle execution. | Same-program integration of the production owner/ACK/CDC/calendar, full connected RTL and source-matched SM/RF/L2/shoreline physical qualification. |
| DeepSeek HBM | Complete static program binding, actual native prefix and immutable restore/reference coverage. | Actual remaining native execution, complete service/owner bridge, connected RTL, full physical/calendar composition and MTP qualification. |

Never promote a directed fixture, software token, area sum, historical clock or zero-overflow placement into the missing gate. Unknown costs must not be zero-filled.

## Qwen ROM: execution, credits and rate reconciliation

### Retained execution and current observation

The retained TP4 numerical result is [captured terminal replay](../results/rtl/qwen_rom_TP4_terminal_20261002/verification_replay.json). The current observer host was built and reviewed separately; the source and input lifetime hooks must be checked at their actual scope.

The current observation runs on **PVE1 PID 2094873**, using:

```text
/home/ubuntu/w12/qrom-observer-host-9d7-20261003-r1/qwen_rom_rt_observed
  --stages /home/ubuntu/w12/qrom-observer-L0-review-f5-20261003-r1/stages-L0-only.txt
  /home/ubuntu/w12/qrom-observer-L0-review-f5-20261003-r1
  /home/ubuntu/w12/qrom-observer-L0-review-f5-20261003-r1/preload.hex
  9223372036854775807
```

Environment includes `RT_QROM_JOURNAL=accepted-state.raw`, `RT_SCALE_LOCAL=0`, and `RT_THREADS=14`. The enormous last argument avoids an artificial short execution ceiling; it is not a predicted cycle count. CPU, file-size and address-space limits were verified unlimited.

At the snapshot the process was live, elapsed approximately twenty-one minutes, RSS approximately 1.4 GB. `accepted-state.raw` was 65,519,616 bytes, last modified at 00:48 UTC. Its buffered output had grown during earlier polls; unchanged file size over a short interval is not proof of a deadlock. `token.log` had only initial image/model loading and the first progress line. No terminal result existed at the snapshot.

Host source digest: `d42a775f630831d3f7640e1b439902f1d3ee07d1b92629375f090a5e4b93b6ad`.
Binary digest: `9d024fc9ae60507bccc339be0dada6af01a0b92abdca12b2bee5c54eb7255ba3`.
Pinned local observer worktree: `/tmp/opentallas-qrom-L0-observation-f5-20261003-r1`.

The observer covers one L0 stage on the ranks, actual owner writes/read responses and final snapshots. It cannot establish a whole-token successor, physical provider ACK, PHY rate or steady decode performance. Historical compiler identity was unavailable for the old binary; the fresh host compiler and artifacts are pinned. Preserve that disclosure.

### What the credits mean

These credits reserve finite in-flight memory cohorts and their distributed storage/lifetime, not compute resources, user requests or MTP tokens. A credit remains owned through capture, masked-write visibility, reader use/debt and reverse acknowledgment/tag retirement. Returning it at backend completion or first data arrival is unsafe.

Even perfectly matched producer and consumer rates need storage for rate multiplied by safe round-trip lifetime. More credits can hide that lifetime; they cannot exceed physical ports, banking, channel tracks or PHY bandwidth. The diagnosed Qwen issue is finite service and ownership, not evidence of insufficient MAC count.

No measured system MFU has yet been produced. Unit-busy cycles in the analytical model are not MFU. The latest user asked for MFU and why rate matching does not eliminate credits; the response remains to be completed after this requested handoff. Explain serial token latency versus steady pipeline throughput: serial layer dependencies add costs, while the maximum stage interval determines throughput only when enough independent items can fill the pipeline. For this heterogeneous architecture, report useful MAC activity, per-unit busy time, memory-port utilization and stalls alongside any explicitly defined whole-system MFU.

### Current finite calendar and rejected credit candidate

The current conditional source-service model assumes cold context service for each layer, context length 8191, four HBM stacks, distributed returns/columns/fill lanes, finite per-group/global/PC ownership and finite bank/lookup/write paths. Production early release is not yet bound. This is an explicitly conditional policy, not proof that the actual retained position-zero token needs the same service.

Baseline finite calendar: `results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json`.
Extra-credit calendar/pricing: `results/uarch/qwen_rom_kv_credit17_20261003/model-r2.json` and `model-r3.json`.

The extra-credit candidate increased the regular group/global credits and pending ownership while retaining the ports and source lifetime. It modeled token time decreasing from 361.0713 microseconds to 358.6013 microseconds, only 0.6888 percent rate gain. It also added known service area while leaving a track deficit and payload/PHY/loaded-route qualification unresolved. It is **REJECTED**. Do not build or tune this candidate. Parent replay regenerated the calendar and composition byte-identically; focused tests, source pins and original pin checks passed.

Independent replay digests:

```text
calendar d8d08f004057530b4c1f11c6f3a072bbe5e756a26175195eb45433056a13d46b
compose  7df91f3da986e6cf909ef3098580657ac8b67d863729c11ebc5ff9fc062d277d
```

The source policy prices 150,847,488 KV bytes per token. The seven-fill-port service lower bound alone is approximately 281.4 microseconds, before other latency. Historical Qwen estimates of 8,460 modeled tokens/s and 6,222 as-built-attributed tokens/s were component compositions, not fully physical qualified results. The new cold-service policy cannot inherit those rates; adding credits cannot remove a port lower bound. Keep workload/context/source policy identities explicit before interpreting the apparent discrepancy.

The unified-model join uses a layer compute-chain budget of 3,338 cycles, a prefix of 451 cycles, and explicit collective conversion. In the extra-credit first-layer calendar, prefix readiness is approximately 0.376 microseconds, fill readiness approximately 9.488 microseconds, and compute completion approximately 12.046 microseconds. These are model timings, not measured MAC utilization or a physical token rate. `baseline_unit_busy` is preserved in `model-r3.json` if needed for scoped activity accounting.

### One next alternative, not a sweep

Ampere's source-owned per-word readiness proposal is worker commit `0fba48658`, clean tree `/tmp/opentallas-qwen-native-local-release-20261002`. Records are under `results/uarch/qwen_rom_kv_dispatch_after_rejection_20261003/`, especially `credit17-rejection-r1.json` and `peer-contract-r1.json`.

It keeps the baseline ports and credits. A word becomes eligible only when all required members have been captured and its masked write is visible. A multiword beat waits for all required words. Reader debt, reverse ACK, tag retirement and cohort reuse ownership remain. Its extra predicate/storage area is an estimate, not a hardware admission.

Russell and Euclid were told to compose exactly one finite replay against actual source observations. Actual rate gain remains unknown. Do not start independent dispatcher, allocator and port sweeps or launch RTL before pricing and acceptance.

## DeepSeek HBM: actual execution continuation and references

### Native prefix and restore

The actual R45 prefix passed PC0–9, with 1,568 outputs, 928 native calls and guarded retirement checks. Its immutable actual journal is approximately 5.4 GB. This is a real prefix; it is not the complete token. Static binding covers the complete program but does not execute the remaining operators.

Kepler owns the continuation at `/tmp/kepler-ds-r50-current-main-20261002`. Committed runner repair `a71c37d4f` provides `tools/ds_hbm_checkpointed_prefix_r55.py` and its R55 storage helper. Parent independently ran the focused tests successfully. The restore must use saved **actual** state, verify it before PC10, preserve the sealed PC9 producer unchanged, and keep producer/continuation engine, witness, storage and journals distinct.

The current blocker is the complete simultaneous inventory and actual constructor preflight, not an arbitrary wall limit. A single-runtime journal estimate is insufficient for the dual continuation. At the previous measurement the large single-journal/checkpoint floor nearly consumed local free disk, leaving only a small remainder before the second runtime and metadata. Recompute fresh free bytes and account for producer journal, continuation journal, dictionaries/indexes, filesystem metadata, checkpoints and simultaneous RAM. Do not launch on the assumption that one journal fits.

At the last parent inspection, Kepler had untracked in-progress files:

```text
results/uarch/ds_hbm_dual_resources_r56_20261003/
tests/test_ds_hbm_dual_resources_r56.py
tools/ds_hbm_dual_constructor_r56.py
tools/ds_hbm_dual_resources_r56.py
```

These were not yet a frozen review commit. Ask for the current SHA and complete projection, review it once, then run the actual preflight and continuation if feasible. Avoid another chain of small preflight-only revisions. Kepler is assigned DS HBM R55/R56; an earlier DS ROM status from that worker was assignment drift and was explicitly corrected.

### Golden/reference coverage: important but separate

Sagan's layer-one extensions and helper dependencies are integrated into main. Parent focused tests passed, and all new expected payload files were verified by raw hash, shape and dtype. PC53–73 adds attention observations; PC74–110 adds actual MoE continuation references. Combined new fields are 7,520. Coverage beyond the original prefix is still only a subset of the full required comparison surface; this is **reference availability**, not a native comparison pass.

Reference helpers include `tools/h4_c0_ds_reference_contract_successor.py`, which translates relocated source paths only when bytes are identical while preserving the old contract identity and fixed expected payloads. Parent replay verified the translations and fields. A checkpoint/reference read for PC78 expert fetch is not proof of actual descriptor acquisition, lease ACK or reverse retirement.

The saved layer-one state agrees with the retained trajectory hash at the reviewed scope. Routed expert identities, shared slot and actual state are preserved in the records. Full old state bytes were not available for every historical record; do not broaden the hash agreement into an unsupported full-byte comparison.

Sagan was asked to create one remaining golden trajectory from the actual saved entering state, with all intermediate observations, followed by parallel family-fragment verification. Do not recompute the already verified prefix for every operator family. The next reference gap includes indexed/query/compressed-history state in the following layer. Confirm the feasible plan and whether a run actually started before reporting progress.

## Qwen HBM and the common hardware/software bridge

The full native numerical Qwen execution covers all layers and head, with complete boundary comparisons and final argmax. Goodall's separate actual KV lifecycle run also passed its scoped data/event/state checks and finished on the large VM. Do not duplicate those jobs.

The original full native execution did not include that complete physical KV lifecycle. The separate run and harness ACK are not an integrated full-program controller/RF/PHY proof. The remaining work is to make the actual production owner, valid/refill/RMW/mirror-ACK/CDC/calendar semantics execute together.

Popper's validity-fence model `0459b4832` is integrated. It requires full-sector valid data for partial K RMW, bitmap-before-record write visibility, both RF home/row copies under a common ACK, and actual position-zero spill. Every positive service cost remains explicit; there is no zero-cost refill, mirrored write or reverse ACK. Parent focused tests and cold replay passed. The storage/area estimate is an analytical screen, not a placed endpoint or RTL admission.

Dewey's next ready installed-calendar successor is **not yet parent-intaken**:

```text
worktree /home/ubuntu/OpenTallas-h3-physical-grants
commit   8ba7384cbb25edf55e29b99429242e392e35b24a
dep      c5e6363f8
record   results/uarch/h3_complete_native_calendar_20261002/installed_services_r2/handoff.json
```

It adds the installed Qwen PC-credit/arbitration model and causal owner adapter: SRAM acceptance/common ACK, parent visibility, consumption, reverse retirement and explicit CDC. Backend completion alone does not qualify retirement. Worker reported focused tests and exact cold replay; independently verify the dependency, source pins and artifacts before integration.

Suggested focused review commands from that tree:

```bash
python3 -m pytest -o addopts='' -q \
  tests/test_h3_complete_native_calendar_installed_r2.py \
  tests/test_h3_complete_native_calendar_grants_r1.py \
  tests/test_h4_hbm_production_owner.py \
  tests/test_h4_hbm_selected_cache_rmw.py \
  tests/test_ds_hbm_additive_endpoint_join_r54.py
python3 tools/h3_complete_native_calendar_installed_r2.py --verify
```

Still unresolved: installed write-credit completion pulses do not yet carry exact tag/generation matching or completion-ready semantics. A safe completion capture and owner matching are required. Round-robin grant-count bounds do not bound elapsed wait until backend/credit delays are bound. Priority starvation under the real DAG remains unresolved. Production C0/SIMD/matrix/KV/L2 need the same installed owner gate with finite consumption, reverse ACK and CDC.

No complete integrated RTL or numerical production job should be claimed merely because the adapter's model tests pass. Popper owns contextual physical endpoint feasibility; Dewey owns calendar/owner composition; Goodall owns the Qwen actual KV/numerical evidence. They must compose one selected contract.

## DeepSeek ROM: current reticle and service work

The selected analytical candidate uses the current no-ECC ROM geometry, stage assignment and reduced per-die parallelism recorded by the model workers. Its summed area is approximately 759.44 square millimetres. That is not a reticle closure or legal routed placement. The fixed outline, literal macro placement, power network, clock/reset, service and communication must all be feasible together.

Current inventory separates core and transport sinks; do not double-count them or discard transport. The selected bank bbox and current-site allocation supersede older annex sensitivities. Keep all predecessor records as history. Do not present an unselected annex or smaller fixture as the selected die.

Archimedes' `bd87257f2` clock/PG audit is integrated. The current raw relay-site assignment **fails**: many branches have no available first-hop site within their timing reach, and even optimistic pin choices cannot reach any raw rectangle for a subset. This does not prove a fundamental reticle-area impossibility. The source-derived repair is to relocate the existing first relay buffers near the upper parents and distribute already reserved raw sites over the full rows. It does not add a new graph or randomly change ROM depth, parallelism or bank count.

Maxwell and Archimedes own **one coordinated fixed-graph repair** followed by actual core-sink assignment, native routing and loaded clock/reset/power checks. The existing supply-shape coverage is not proof of external feed/via/sink legality or extracted skew. Track capacity is tight before complete power/clock allocation. Ask for their current frozen SHA rather than consuming a mutating worktree as evidence.

The predecessor balanced selector failed payload timing and hold. Its failure is preserved; do not round the target period, loosen uncertainty or adopt the failed selector. Epicurus owns any selected structural selector work under the same model and closure gates.

Nash's finite service work (`e380a8e13` at the last parent snapshot) defines post-write visibility and reader timing, actual tile-writer hooks and separate version/address leases through read-plus-return tags. It still needs the full selected context calendar, actual simultaneous version lifetime and CDC/physical timing composition. Minimum storage/version counts are lower bounds, not an admitted maximum live inventory.

Hubble owns actual DS ROM instruction/deadline interpretation; Peirce owns checkpoints and recoverable state. Original L0 terminal evidence has no final exact DONE. Diagnose actual ready/return/write-ACK progress rather than inventing an arithmetic stall from a PC number. A conditional calendar cannot certify healthy progress of a different historical live configuration.

## Fleet and protected jobs

| Resource | Current policy and work |
|---|---|
| Local `/home/ubuntu/OpenTallas` | Integration, model/replays, native execution preparation; actual RAM/disk inventory before large continuation. A local Yosys proof was live at last prior poll; verify PID before changes. |
| PVE1 | New admitted work allowed; protected Qwen L0 observer and surviving large OpenROAD global placement. |
| PVE2 | Drain-only. Protected old detailed-route job; no new placements, builds or requeues. |
| PVE3 | Drain-only; last report was release-ready with no heavy job. Confirm before telling owner it is empty. |
| Large VM `155.103.253.226` | Active large-memory resource; Qwen KV run finished, available subject to current occupancy. |
| Original AGIdock VMs | Retired. Do not reopen or assign. |

PVE2's last inspected route PID was `551255`, near its late iteration with a small violation count. No final timing result was available. Local proof PID was `1998275`, output rooted at `/tmp/qrom-issue-lockstep-760a-r2`. These are prior polls, not freshly verified running-state claims.

### PVE1 physical job: preserve, but do not claim historical continuation closure

PVE1 **PID 2006920** was freshly verified live at the snapshot, OpenROAD global placement, approximately 87 GB RSS, with cumulative CPU time advancing. It uses the old source/configuration. An old launcher wall deadline caused temporary-directory cleanup while the container process survived. Do not kill or restart it.

Current-stage retention restored the `/work` mount to:

```text
/home/ubuntu/ot-retained/pve1-w11-su2-live-20261003/work
```

The passive watcher is service `ot-pve1-su2-live-retention-20261003.service`; its previously observed PID was `2093643`. It uses read-only collection of deleted/open files and preserves file offsets. The current-stage source and log files were retained. The **original closed/deleted `2_floorplan.sdc` was not recovered**.

This missing SDC matters. Current global placement writes its database/reports/metrics but no replacement SDC. Later stages need the predecessor SDC to continue. A newly generated constraint file is not byte-identical historical evidence. Do not inject Tcl, a debugger, hooks or substitute constraints into the live process.

Chandrasekhar owns retention and a separate explicit **new-source constraint successor**: when a current database is available, use pinned clocks and complete endpoint coverage for a new SS/FF run, label it as a successor, and keep historical continuation unqualified. Model/review that successor before launch. Do not spend more time searching repeatedly for the unavailable old closed file.

Retention and writer-gate evidence is in:

```text
results/rtl/pve1_live_work_retention_recovery_20261003/
results/rtl/pve1_live_work_retention_recovery_20261003/sdc_writer_gate/
```

For future physical jobs, `tools/run_abi3_physical_persistent.py` is the reviewed persistent-work wrapper. It retains success/failure outputs and does not impose an arbitrary subprocess wall ceiling. Do not retrofit a running old job merely to use it.

### Safe status commands

Use short read-only SSH operations. A tool-output wait timeout is not permission to impose a timeout on the underlying experiment.

```bash
ssh ot-pve1 'ps -p 2094873,2006920 -o pid,etime,time,rss,stat,args'
ssh ot-pve1 'stat -c "%s %y %n" /home/ubuntu/w12/qrom-observer-L0-review-f5-20261003-r1/accepted-state.raw'
ssh ot-pve1 'tail -20 /home/ubuntu/w12/qrom-observer-L0-review-f5-20261003-r1/token.log'
ssh ot-pve2 'ps -p 551255 -o pid,etime,time,rss,stat,args'
```

Inspect exact command lines and file ownership before signalling any PID; PID reuse is possible. Do not use a broad `pkill -f` that may match a watcher, another worker or itself.

## Agent assignments and continuation addresses

These are current-session agent identifiers. If the next session cannot reach them, reconstruct each stream from the worktree/record, preserve live jobs and assign replacements without duplicating an expensive artifact. Worker responses requested during handoff may arrive after this snapshot.

| Agent | Identifier | Owned work |
|---|---|---|
| Hubble | `01a0f95d-bab7-79d2-957a-66038ae5ec3e` | DS ROM deadlines/actual instruction progress. |
| Peirce | `01a0f95d-badc-74d3-bde3-f3eb28f089b8` | DS checkpoints and recoverable actual state. |
| Nash | `01a0f981-cb25-7240-9713-de4590db46f9` | DS ROM finite writer/reader/version service. |
| Maxwell | `01a0f9a9-6ef1-7d91-8660-0d51c96a09c0` | DS literal reticle placement and physical repair. |
| Archimedes | `01a0f9aa-9568-73d2-a794-26b33a55fb4d` | DS clock/reset/power/site reach composition. |
| Kepler | `01a0f9c6-fde3-7111-8b3c-a4a505b9a010` | DS HBM actual continuation and complete dual-runtime resources. |
| Epicurus | `01a0f9c9-08b8-7661-aec0-99f85fde09d1` | DS selector structural/physical path. |
| Sagan | `01a0fa84-2959-7963-b1d4-b377be694aee` | DS remaining numerical reference trajectory/observers. |
| Euclid | `01a0fab1-2dbc-74c3-a225-72b1f846f3aa` | Qwen ROM capture/source-lifetime observation. |
| Goodall | `01a0fac5-13d3-7342-9968-dca7cded62e3` | Qwen HBM actual KV and numerical evidence. |
| Popper | `01a0fc12-35b5-7621-9d9d-7837163c53b0` | HBM physical endpoints, validity/RMW/common ACK. |
| Dewey | `01a0fc12-35e2-71f0-873e-d6aa6ab2d24e` | HBM installed calendars and production owner integration. |
| Russell | `01a0fd4d-36ca-7780-9515-f0094cf8cae2` | Qwen finite credits/calendar/rate reconciliation. |
| Chandrasekhar | `01a0fd5b-5719-7d42-9c49-f60492d5cd5a` | Fleet, persistent physical retention, safe source successor. |
| Ampere | `01a0fd69-551c-7521-bb30-67c4bd8c3c6b` | Qwen channel/port/source-owned dispatch proposal. |

The parent owns integration, independent review, scheduling conflicts, source/configuration identity, cross-target model composition, risk communication and final claim audit. It must relay contracts when peer tools are unavailable. Do not let separate workers independently change the same source policy or physical geometry.

## Risks that can still invalidate the performance claim

1. **Finite service and ownership:** safe data visibility, credits, tag generations, reverse retirement, bank/port contention and CDC may dominate the token even when matrix arithmetic is fast. Qwen's rejected extra-credit candidate demonstrates that larger queues alone are insufficient.
2. **Literal physical composition:** symbolic area and empty-row reservations do not prove reachable clock relays, legal power feeds, loaded timing, reset, selector or route capacity. DeepSeek's failed site assignment is a concrete example.
3. **Software/hardware feasibility join:** complete native numerics and directed RTL are separate results until the emitted program executes through the actual finite controller/RF/owner contracts.
4. **Calibration and workload mismatch:** cold context versus retained position-zero work, historical component rates versus actual service, and inferred versus measured synchronization can change the rate substantially. Always join the same program and configuration.
5. **MTP acceptance:** a speculative headline depends on validated verify/drafter cost and representative accepted-token statistics. A convenient chat assumption is not the requested agentic median.
6. **PHY/package assumptions:** aggregate internal ports are not proof of usable shoreline payload bandwidth. Protection, routing, placement, clocks and realistic source-matched PHY boundaries remain part of the research claim.

These are architectural/feasibility risks. Unfinished engineering tasks listed above are the work intended to close them; completing a task is not automatically evidence that the corresponding risk is closed.

## Review and publication workflow

For each next milestone, request a frozen worker SHA, clean status, exact changed paths, dependencies, source/tool/input pins, replay command, terminal evidence and disclosed limitations. Inspect the dependency first; cherry-pick only the bounded changes into a clean review tree. Independently run meaningful focused tests and cold regeneration, verify every referenced artifact hash and preservation of pinned originals, and compare failures against the same main baseline where relevant.

Do not rerun large numerical/physical jobs solely to repin equivalent paths. Use a recorded identical-byte successor where permitted, preserving the historical identity. Conversely, never use path translation to hide changed source bytes or broaden an old pass.

After integration, run the figure/readiness checks, explicitly stage the milestone paths, commit and push main. Keep the active goal incomplete until the matched-configuration G0–G5 audit passes for all claimed modes. A passing publication consistency check may coexist with blocked final gates; report both honestly.

For cleanup, `git worktree list --porcelain` is the current inventory. A snapshot was written to `/tmp/opentallas-handoff-20261003/worktrees.txt` during preparation, but it is only a convenience copy. Do not remove a worktree because its branch is old: inspect dirty files, lightweight refs, worker ownership and all live process paths first. Previous retirement reclaimed substantial disk without deleting unique sources or active checkpoints; apply the same rule.

## Remaining user-facing answer

The user's immediately preceding question asked whether single-user MFU is low, whether stages are imbalanced, and why rate-matched pipelines need credits. The parent checked `model-r3.json` but has not yet delivered the full answer because the user requested this handoff next. Do not claim an exact measured MFU. Explain the difference between serial critical-path latency and multi-item steady throughput, then show the conditional memory-service contribution and safe in-flight lifetime. A useful next measurement is per-unit active useful-MAC cycles, port busy time, credit stalls and dependency waits on the same actual program; the present analytical `unit_busy` counters cannot substitute for that measurement.

## Fresh worker updates received during handoff preparation

These frozen reports arrived after the initial snapshot and supersede the earlier “in progress” status where indicated. They have **not yet been independently parent-intaken**. Worker-reported validation is identified as such; do not infer parent review or main integration.

### Kepler: aggregate resource plan frozen; constructor preflight is live

R56 is now clean at `6f8ea7ec4ef66045fbf8c6a4e00604ce8d23f415`, same Kepler worktree/branch. Worker reports ten passing tests, thirty-three source pins and preserved refusal drafts. The composed new disk requirement is 525,569,405,088 bytes against fresh launch availability of 806,361,690,112 bytes. Producer/cold-constructor coexistence RAM is 119,463,128,716 bytes against 143,403,999,232 bytes available. This replaces the old incomplete single-journal projection, but still needs independent review.

One **constructor-only** preflight is running locally, PID **2548073**, approximately 1.93 GB RSS at the worker probe. No native PC or numerical continuation has launched. Preserve this run and inspect its terminal receipt:

```text
output /tmp/kepler-ds-r56-dual-constructor-preflight-20261003
log    /tmp/kepler-ds-r56-dual-constructor-preflight-20261003.log
launch /tmp/kepler-ds-r56-dual-constructor-preflight-20261003.launch.json
```

Exact command:

```bash
/home/ubuntu/bin/python tools/ds_hbm_dual_constructor_r56.py \
  --plan results/uarch/ds_hbm_dual_resources_r56_20261003/preflight_plan.json \
  --out /tmp/kepler-ds-r56-dual-constructor-preflight-20261003 \
  --preflight-only
```

Next: independently review the aggregate inventory and source pins, collect this same preflight's positive/negative terminal evidence, then authorize execution internally within the owner's existing scope if all admission conditions pass. Do not duplicate the constructor or claim it proves restore/numerical/physical qualification.

### Russell: the one per-word dispatch alternative is also rejected

Frozen commit `b2a8668f7ec5774520ca9fb0acb63d8cb3c69e35` is directly atop parent `7c3fb3e43`, clean in `/home/ubuntu/OpenTallas-qwen-kv-beat-retirement`, branch `codex/qwen-kv-beat-retirement-20261003`. No owned live jobs. Records and replay instructions are in `results/uarch/qwen_rom_kv_beat_retirement_20261003/REPLAY.md`.

The Ampere-joined alternative preserves baseline ports/credits and charges the additional predicate/storage once. Worker reports conditional full-token latency **358.013133 microseconds**, gain **0.8542 percent**, below the adoption threshold, with the same unresolved channel deficit and physical costs. Verdict **REJECTED**. No RTL/P&R/capacity sweep was launched. The group-credit necessary bound under the new lifetime does not reopen the rejected extra-credit design.

Worker reports six passing tests, fifty-seven source pins, twenty-eight preserved originals and a full causal cohort record set. The composition was independently verified within the worker stream; a second independent parent full-calendar replay has not been performed.

Suggested intake verification:

```bash
python3 -m unittest discover -s tests -p 'test_qwen_rom_kv_beat_retirement.py' -v
python3 tools/verify_qwen_kv_beat_retirement_evidence.py
```

Next input is Euclid's **existing** L0 actual producer/state/residence/release/reader/ACK journal, then source-policy traffic reconciliation. Neither rejected candidate receives further tuning or build effort. Historical headline rates remain incompatible with the conditional cold-service transport lower bounds; no larger port replication or traffic-reduction policy has been selected.

### Maxwell: fixed-graph clock repair and named completion-hook reservation frozen

Clean committed portion is pushed at `2ae90a0116f20654005e479fec2f1b951a014b8f`, worktree `/home/ubuntu/dsrom-capture-home-20261002`, branch `codex/dsrom-capture-home-r49-20261002`. Clock-repair predecessor is `53dfdf1c9d2bdc4d6a88a24fd785529b1ffad75d`. Main remains untouched.

A completion hook and two local clock/reset buffers are reserved in the existing identity-strip tail, disjoint from current identity cells and bank/clock inventory. Worker reports combined tests, byte-identical cold outputs and artifact hashes verified. These are reservation/model results, not loaded timing or absolute deadline qualification. Evidence: `results/uarch/dsrom_capture_completion_hook_slot_20261003/{handoff,model}.json`.

Dirty excluded WIP remains:

```text
tools/dsrom_capture_user32_codec.py
tests/test_dsrom_capture_user32_codec.py
results/uarch/dsrom_capture_user32_codec_20261002/
```

Do not integrate that WIP by staging the whole tree. No owned persistent or remote job. Next: bind downstream relay/pad branches, power and the hook's clock/reset to qualified parent routes; join actual visibility/captured-credit/completion/read/return callbacks with Nash and Hubble. Absolute deadlines, CDC, loaded SS/FF and contextual P&R admission remain open.

### Chandrasekhar: explicit new-constraint successor prepared; original job unchanged

Frozen default-off preparation `8c6d4a3f3d7fcb39dafe21eb9e2621641c8c0664`, clean worktree `/home/ubuntu/pve1-source-constraint-successor-20261003`, branch `codex/pve1-source-constraint-successor-20261003`, directly based on `7c3fb3e43`. Records: `results/rtl/pve1_new_source_constraint_successor_20261003/plan.json` and `validation.json`.

The new contract pins the original clock/uncertainties/I/O/reset exception and adds no model cycles. It requires complete independent endpoint and exception coverage, macro timing reconciliation and full SS/FF. Worker reports focused tests, original RTL hashes and artifacts verified; a separate sparse-checkout discovery failure is disclosed. **Physical qualification is NOT_RUN.**

At approximately 01:01 UTC, PVE1 OpenROAD and watcher remained live; no terminal ODB had been emitted. PVE2 remained at its retained late-route progress; PVE3 had no matching heavy process. No job was restarted, signalled or injected.

Required next sequence: obtain a successful terminal database, review the constraint plan, prepare/review a persistent database-stage driver plus native endpoint audit, and only then launch a fresh disjoint lease. The existing persistent wrapper is synthesis-oriented and **must not be mistaken for an ODB-resume command**. Historical SDC equivalence remains unclaimed.

### Dewey: installed-calendar ready snapshot reconfirmed

Ready/dependency SHAs are unchanged. The worktree has no tracked modifications and no owned live jobs. Six untracked earlier intermediate entries remain under `results/uarch/h3_complete_native_calendar_20261002/causal_grants_r1/`; preserve them and do not stage them blindly. Committed causal evidence is in `final_causal/` and the new installed-service evidence in `installed_services_r2/`.

Next implementation is actual emitted contender identity/lease binding and SRAM ACK/visibility/consumer/reverse receipts. Completion tag/generation matching, backpressure and finite CDC/service bounds remain required. R56 constructor success, if obtained, is a separate resource prerequisite and does not close this hardware ownership join.

## Corrections appended 2026-10-03 (publication of corrected numbers)

These corrections leave the snapshot text above as it was written. Where it disagrees, they take precedence. The corrected figures and their sources are in [HEADLINE_BUNDLE_SCOPE.md](HEADLINE_BUNDLE_SCOPE.md), section "Corrected numbers — published 2026-10-03".

- **KV bytes label (the "150,847,488 KV bytes per token" sentence in the Qwen ROM section).** 150,847,488 B is the RD+WR **command** bytes: 4,713,984 commands × 32 B. The KV payload is 150,690,816 B read off chip and 156,672 B written, per die per token. Source: `results/uarch/qwen_rom_calibrated_calendar_20261003/baseline-r1.json` `identity`, from branch `claude/qwen-kv-streaming-20261003` @ `bb65ae0dc`.
- **TP-2 banner on the retained TP4 token.** The pinned record `results/rtl/qwen_rom_TP4_terminal_20261002/original_terminal.json` has a `claim_boundary` banner that reads "G=5,120 TP-2 dies". Its `design_point` is `tp=4`, `groups_per_die=6144`, `kv_fp8=true`. The design point is correct and the banner is stale. The record stays pinned and unedited; this note is its annotation.
- **What the TP4 token proves.** The token proves datapath and numerics only. The runtime die wrapper ties KV, weight and embedding readiness high: `kv_write_drained`, `kv_ok`, `w_ok`, `emb_ok` and `me_mem_ok` are all `1'b1`, and the embedding ROM data is zero (`rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv:151-165`). It is not evidence of KV service, weight delivery or rate.
- **Qwen ROM rate.** 8,460 and 6,222 tok/s are compute-chain compositions with no KV-delivery term, and 6,222 also mixes positions. Both are superseded. The calibrated finite-calendar figure is 357.99 µs = **2,793 tok/s** per user at 8K (decode position 8,191, batch 1, AR, FP8 KV). This is model only, calibrated with the measured 4,668-cycle RTL layer. The near-HBM attention entry selected for build is 190.97 µs = **5,237 tok/s**. This is model only, on unqualified HBM and closure inputs.
