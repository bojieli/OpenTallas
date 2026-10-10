# Current Codex → Claude handoff — 2026-10-09

Snapshot: approximately **01:30 PT / 08:30 UTC**. This is today's continuation record; older handoffs are historical. Work and remote jobs continue. Nothing here establishes complete token-level or die-level closure.

**Coordinator:** Codex `/root` works in `/home/ubuntu/OpenTallas`, branch `main`, integrating and pushing completed steps. Owners use the worktrees below. Their latest commits may be ahead of main; inspect branch ancestry before integrating. Never run git in another owner's worktree, stage with `git add -A`, or expand sparse checkouts. Some intentionally incomplete checkouts show unstaged deletions; these are not source removals.

**Execution constraints:** no new compute on localhost. Use EPYC1/2/3/4, PVE1 and AGIdock with measured RAM/disk admission and future-growth reservations. Preserve progressing jobs, completed objects and immutable failures. New modeled/elaborated RTL enters physical work alongside exactness; exactness gates adoption. Latest owner Option B is TT setup ≥0 / FF hold ≥0 / DRC 0, SS sensitivity, at actual implemented clocks/boundaries with 60/25 ps uncertainty. Do not substitute slower SDC clocks for hardware. ROM has no ECC; mutable SRAM/HBM/link/control protection remains required.

**Current progress and failures:**

- Qwen S7 controller standalone route: TT +130.52 ps, FF +5.25 ps, DRC 0; four-rank argmax collector: TT +210.29 ps, FF +9.57 ps, DRC 0. Both have negative SS sensitivity and incomplete production joins.
- Real W1 ROM→dequant join, transient speculative KV storage, distributed DeepSeek HC reader/mean/join, native MTP transaction/emit mechanisms, authenticated MT_SEED5 transport, protected host and Engram lead have component gates. Physical successors are queued/running; these are not complete numerical-token proofs.
- Original MTP campaign 14 fails (2,125 state / 731 output differences), first divergence at position 1 before rollback. Repair owner found NSLOT=1 clears DYN25/26 despite ring8 ISA needing position-dependent offsets; default-off repair is implemented, verification pending. Campaign 19 passes different layers.
- Qwen argmax/dequant physical attempts fail pin density; W1 bank has macro-pin maze-access failure. Qwen KV merge DRC spacing and collective pin-placement successors are queued. Q5 remains in physical work.
- DeepSeek HC original routes expose SECDED encode/decode timing and local congestion; registered encoder/decoder successors have exact gates and active physical work. S81 FIFO RVT misses setup by 0.75 ps; selective driver ECO is under examination. Native Q calibration requires corrected post-CTS H1 hook ordering.
- TA15 boot/reset digital body remains physically unqualified: latest TT −215.27 / FF −17.72 ps, DRC 0; asynchronous reset recovery and first CDC stage remain open. HBM W2 needs real phase/hold/reset structural repair.
- NK4 flat synthesis and legacy Qwen r22 die routing OOM failures are preserved. NK4 hierarchy elaboration now passes; no flat retry. Legacy r22 is superseded. Actual quarter lint passed at ~91 GiB peak.

**Owners and source directories.** Paths below are relative to `/home/ubuntu/`; names are Codex task names. Several owners have additional pinned remote build trees. The fleet state is authoritative for current execution.

| Owner / task | Worktree(s) | Current implementation or closure work |
|---|---|---|
| `ds_control` | `wt-codex-ds-control` | Native compiler, authenticated seed transport, existing VM-read-port sharing, shared-LAST consumer, Engram completion and runtime PC debt/lease. |
| `embedding_hbm` | `wt-codex-emb-hbm` | Actual 32-PC embedding hierarchy, native provider/ordinal/write-ledger binding, real relay stations and physical integration. |
| `embedding_hbm/real_port_wrappers` | `wt-emb-real-ports` | Completed wire wrappers/gates incorporated into parent; clean and idle at last report. |
| `engram` | `wt-codex-engram-resume` | Released token map/history lead, protected mutable history, DEAD/rewind metadata, lookup completion and installed aperture binding. |
| `fleet_closure` | `wt-codex-fleet-recovery-20261008` | Queue/admission, failure triage, result integration, resource claims and live registry. |
| `hbm_continuation` | `wt-codex-hbm-indexer-recovery`; `wt-codex-hbm-coll-capture` | NK4 hierarchical mapping; protected query/formatter joins; collective capture/route. |
| `hbm_continuation/selector_capture` | `worktrees/hbm-selector-capture-sparse` | Native selector capture/calibration and routing. |
| `hbm_continuation/service_recovery` | `wt-codex-hbm-service-striped-20261008` | Actual controller + protected mailbox + service-core join; publication/credit contracts. |
| `…/timed_iks_gate` | `worktrees/hbm-iks-timed-refpb` | Native protected SRAM selector, retention and mapping. Mapped complementary control protection failed: mirrors merged; no adoption. |
| `hbm_system` | `wt-codex-hbm-system-resume` | Native index control, candidate publication store, compressor/key path, VM8 repair and KV-shadow continuation. |
| `hbm_system/hc_shard` | `wt/codex-hc-row-shard-r2` | Full HC capture, lease/epoch checking, retained control protection and physical context. |
| `hbm_system/link_retry` | `wt/hbm-link-retry-20261008`; `wt/hbm-retry-pipeline-20261009` | Collective publication/release, actual link capture, protected retry pipeline and routes. |
| `hbm_system/expert_steering` | `wt/codex-w2-phase-seat` | W2 per-word phase copies, hold-safe seats and reset-release repair. |
| `hbm_wiring` | `wt-codex-hbm-wiring-20261008` | Native die topology/pins, TA15 reset/CDC, loader clock diagnosis and fresh CP/MTP slot binding. |
| `ingest` | `OpenTallas-ingest-recovery` | Protected native host/router, per-PC arbitration, actual capacity/region inventory and lease binding. |
| `mtp_die` | `wt/codex-mtp-die` | MTP/WB layout, twelve-head allocation, distributed HC homes and selected three-expert P2 transport. |
| `mtp_rom` | `wt/codex-mtp-wfc-recovery` | Coordinates seed/shared/head/route work below. **Do not merge this old branch wholesale:** only the shape-audit commit `7c2f929ff` is intended from it. |
| `mtp_rom/draft_p2` | `wt/codex-mtp-shared-producer`; `wt/codex-mtp-seed-qs5f`; `wt/codex-mtp-wfc-token-r3-route` | Production seed, shared-result endpoint, real W2 producer/visibility/read lease and WFC routes. |
| `mtp_rom/embed_port` | `OpenTallas-md6-embed` | Released head images, actual B→A→Markov bundle/tails and two-edge ping-pong ROM capture. |
| `mtp_rom/markov_route` | `wt/codex-markov-route`; `wt/codex-markov-pinreg`; `wt/codex-mtp-vmx-route`; `wt/codex-mtp-p2-route` | Markov, VMX, lookup and finite P2 transport physical work. |
| `qwen_hbm_unify` | `wt-codex-qwen-r25` | Actual numerical quarters, OWNER_W74 identity, query-release/VM ownership and native program binding. |
| `qwen_hbm_unify/cmdproc18` | `worktrees/qwen-cmdproc18-20261008`; `worktrees/hbm-cp-mtp-native-20261009` | Native ROM compiler/bridge; fresh CPsouth MTP facade, transaction guard and emitted-token queue. |
| `qwen_hbm_unify/fmt3` | `wt-qwen-fmt3` | Wide physical masters, exact pins, pipelines and source-matched route budgets. |
| `qwen_hbm_unify/stage_harness` | `qwen-r25-stage` | Real N256/M64 numerical quarter and finite memory/publication tests. |
| `qwen_system` | `wt-codex-qwen-system-20261009` | Resident payload/layout, finite PC ordinal owner, KV row/merge, metadata and descriptor/fence joins. |
| `qwen_system/crom_control_physical` | `wt-codex-qwen-crom-ctl` | CROM/control routing; registered SRAM/ECC output capture and command-station repairs. |
| `review_dsrom_token_path` | `wt-codex-dsrom-mean-capture-20261009` | Actual HC reader/mean/seed joins and SECDED pipelines; leases/VM arbitration/native transport integration. |
| `review_hbm_token_path` | `wt-review-hbm-token-fifo-20261009` | Native 201-bit MTP lowering, real backend and argmax binding, coordinated reset/protected state. |
| `review_qwen_token_path` | `wt-codex-qwen-q5-20261009` | S7 backend, W1 banks/dequant/broadcast, transient KV, attention/RoPE and physical failures. |
| `s81_continuation` | `wt-codex-s81-cfifo-rd-eco`; `wt-codex-s81-native-q-hold`; `wt-codex-s81-r4c-sparse` | FIFO driver ECO, Q H1 hook, real scan/head corridor and slot reservation. |
| `s81_continuation/dies_scan_head` | `wt/codex-s81-scan-head-sparse` | Fixed-outline field/service geometry and real macro/pin inventory. |
| `s81_continuation/service_q_repair` | `wt-codex-s81-fused-head-boundary-20261008` | Fused head boundary detailed route and timing qualification. |
| `mtp_numerical_repair` | `wt-codex-mtp-numerical-repair` | Original campaigns 14/15/19/20: instruction snapshots and ring-address correctness repair. |

**Read the live evidence here:**

- Actual Claude trajectory: `/home/ubuntu/.claude/projects/-home-ubuntu-OpenTallas/528876d6-b73d-44f4-be27-5d8ea084692b.jsonl`; original pane `3:1.0`. Latest pane read still showed the rate-limit screen; elapsed reset time alone does not prove resumed work.
- Jobs/events/handles: `~/.local/state/closure_loop/jobs/*.json`; daemon log/heartbeat and deferred merges alongside them. Intake: `/tmp/claude-review-20261003/closure_jobs`.
- Daemon source: `/home/ubuntu/wt-codex-closure-daemon-20261007l/tools/closure_loop/closure_loop.py`. Live element API: `http://127.0.0.1:8765/api/elements`; additive records: `results/fleet_viz/element_registry/`. Latest fleet report: 72 records, zero schema errors.
- Distributed HC handles: `results/fleet/dsrom_hc_distributed_jobs_20261009.json`; Qwen native jobs: `results/arch/qwen_q5_20261009/native_active_jobs.json`.
- Preserve live original T1 builds, native MTP STOP `hfd-mtp-x-stop-4386513e4-tc`, selector `hbm_idx_sel_native_qend_aa7127b87_pathfinding`, collective capture/baseline, embedding jobs, HC/retry/VM/KV-shadow and Markov/P2/WFC jobs. Re-read actual handles before restarting or retiring anything.

**Next priorities:** integrate ready owner commits; close measured structural failures; bind real native backends, memory ownership and visibility fences. Specifically, fullshape linked MTP kernel images/argmax, Qwen S7 numerical backend, shared-W2 instruction/VM namespace and read lease, installed HBM region inventory, candidate-store protection and TA15 asynchronous reset remain unfinished. Golden expert W2 results are BF16-rounded before widening and sequential FP32 expert accumulation; native transport carries widened 32-bit values, not an invented packed BF16 stream.

Latest interface change: native MTP needs 18 actual argmax/result input bits, so the new CP-facing contract is **197 bits**, superseding the unqualified 179-bit facade candidate. Preserve old route evidence; coordinate `review_hbm_token_path`, `cmdproc18` and `mtp_die` before physical submission. `mtp_die` also owns the actual ordered A-prefix accumulator (+0, E0, E1, E2); the shared producer and final shared-LAST consumer remain separate owned work.

Root is preserving source unions and missing unified-model hooks during merges. Main integration hold: `~/.local/state/closure_loop/main_integration_hold.json`; measurement and closure-record mergers now defer under it without stopping compute. Remove only a hold you own. The new STA reporter preserves stderr/process status and treats missing/non-finite metrics or Tcl errors as failures; its five receipt tests passed remotely. Do not overwrite historical verdicts or call a component gate complete end-to-end closure.
