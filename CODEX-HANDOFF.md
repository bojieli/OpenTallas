# OpenTallas — current Codex handoff

Updated 2026-11-06 00:02 PST. Current work only; historical evidence stays in lane files and the queue.

Claude stopped on the weekly limit; reported reset **2026-11-12 04:00 America/Los_Angeles**. Codex continues all lanes until explicitly told to hand back. Read `CODEX-ROLE.md`. Owner questions go as plain text under OWNER? in `CODEX-LOG.md`; keep working, never open a blocking dialog.

## Progress

Latest cached census: **2026-11-05 23:05 PST, 167 signed items**. No new census was run for this summary. Counts are physical core implementation views (module + outline + pin table), not merely module names.

| Die | Signed core views | Signed partition types |
|---|---:|---:|
| S81 | 52/58 | 5/205 |
| HEAD | 4/4 | 12/25 |
| Qwen compute | 18/20 | 0/119 |
| Qwen KV/system | 28/32 | 0/56 |
| HBM | 48/102 | 0/81 |

Totals: **150/216 core views; 17/486 types**. HBM's module-only count is46/94; its old101-view denominator predates the q3 split. There was no two-core regression. Subsequent plan events can add or replace required views.

**No complete die release exists.** Remaining release work includes current partition views, real-view parent composition, die routing/clock/STA and token qualification. Component or bounded-region passes are not whole-die passes.

New results not yet incorporated into that census: KV ORDER qualified (credit submitted); S81 t46 re-signed LOCAL_PASS_NEEDS_PARENT; HBM brmw current-tag SIGNED+LEC. IDX's signed child is not its still-unsigned parent core.

## Execution rules

- Follow `AGENTS.md`, `BRIEFING.md` and latest owner decisions. The intel2 coordination queue carries newer rulings than some historical methodology copies.
- Clock **833ps**, setup **TT**, hold **FF**, never SS for closure. Released owner12.24b/c uses **0ps setup uncertainty /25ps hold**, old60ps setup margin INFO. Do not change constraints during takeover.
- **Review before route:** render, actually inspect, record image/findings/verdict in `results/geom_review`. Check dataflow, faces, reach, density, macro channels, clocks and PG; fix bad geometry before routing.
- Failing cores get parallel targetedA and genuinely conservativeB (registered faces, <=150k functional cells, util<=.45, short reach/reset locality). Inspect actual generated config: explicit CLI settings previously lost to recipe defaults. Two structural strikes require a new form; few-endpoint residual ECO is permitted.
- RTL stays exact: smallest meaningful lockstep/formal plus mutant, kit LEC for adoption. Declare every added cycle to TOK/model. Preserve failed evidence. Only released sign-off qualifies; later owner policy accepts LOCAL_PASS_NEEDS_PARENT for local counting, not die release.
- **Hub=intel2. Localhost `/home/ubuntu/OpenTallas` is protected owner's checkout: no git there.** Own `codex/*` worktrees only. Heavy work via intel2 `ot-run`, measured RAM/disk admission. Preserve live jobs; do not duplicate them or kill another lane's jobs.
- Never edit scripts a live job reads. Fresh recovery copies and matched tool cohorts. No stash, force push, add-A, ours/theirs merges or deletion of others' unique work. Merge under intel2 lock, resolve in own branch, push and confirm HEAD==origin/main.
- Cleanup only approved exact scopes/manifests; preserve actual SIGNED/.keep/live/bind/unique state. Root floors: epyc2/4=500GB, intel=150GB, epyc5/6=100GB. Follow admission guards.

## Remaining 12 non-HBM cores (ledger basis)

| Core | Current action |
|---|---|
| S81 BKSEL Q | LEC66785EQ; internal-SRAM hold repair remains negative but progressing. Not an external-port padding case. |
| S81 ENG RR E | Measured IO-reference recovery in GRT; original congestion0, timing frame was mismatched. |
| S81 IDX TX | Child SIGNED TT+4.48/FF+.13 and routedLEC5385EQ. Current-tag view then real SPLIT2 parent; canonical hard-child generator support being integrated. |
| S81 COLL E/W | Old forms preserved; conservative west M6-access estimate0overflow, full sample inGRT. East follows qualified form plus plan/OBS allocation. |
| S81 ROM Q | HW half DRT complete DRCempty/ANT0, finish/RCX/signoff next; HE LEC47533EQ/GRT active. Both halves and real hard-child parent still required. |
| QC NK | Protected-data-repeater obstruction fixed; GRT setup table positive/TNS0, final routing/signoff still pending. |
| QC NL | Corrected macro/pin form inDRT; parallel routed-form ECO active. Current child/model LEC collection continues. |
| KV ORDER | Qualified TT+8.66/FF+4.48/DRC0;16remaining proof cones BDD UNSAT; count credit submitted. |
| KV PEER | Corrected .40/M7 reset/locality A/B queued. Admission being right-sized from measured29.8GiB whole-container peak, only own unstarted clients replaced. |
| KV PROMPT | RoutedLEC32050EQ; DRT active with oscillating violations. Preserve progressing form; true .40 fallback prepared if required. |
| KV INGEST | New form proof67309EQ+mutant, actual .40/M7 verified; admitted and nowCTS. |

## Other active work and owners

- **S81 (`s81`, `s81_core_results`, `s81_types`):** remaining cores above; dedicated leaf/station conservative-form lane owns17 genuine held types. Reset-family and two tap moves merged. Old -378ps FT failures were stale pre-I39 kits; current plan already166.6ps, so only exact missed retries released, no new timing relaxation.
- **HEAD/QC (`qc_head`, `head`, `residual`):** HEAD n4 FREG/WREG event merged, +1data on4links/K+2, real physical trial live. Final START face-placement fix merged. QC SLECTL split has10 small child masters; source/guard integration and builds active.13/14 old QC holds cleared from actual pilot/fix evidence; HC0 remains genuine reform work.
- **KV (`kv`, `order_peer`):** cores above; short landing status-lap alternative exact/proved/defaultOFF, physical A/B queued. PHY reset3stations/+3boot event merged. HubWi must use typed-core overlay: bounded FIFO declarations alone do not solve historical whole-HR inlining. KV08 witness-pad explanation is unproven and held; observer traces actual native witness before any plan change.
- **HBM (`hbm`, `gaps`, `wbq_safe`, `hbm_forms`, `vms_safe`, `bank128`):** q3 SRAM right-width macro fix, clock-pin separations/TX taller slot, TX header source, SVGR RF1 source integrated. Safe WBQ split/parent allocation, bank128 write-face, N4 macro-access, EXPX shallow-clock and remaining core forms active. brmw qualified; h9b and ECO results collecting.
- **HBM parent (`hbm_parent`):** current real-view q_su21 bounded trial with16signed lane1 children. q_spb2 direct kit hit same-face-slot schema issue; selected useful alternate instead of waiving it. Current type matches retained native m79f bind body exactly.
- **HBM projection (`hbm_projection`):** production native two-half projection compiler gap being filled. Canonical root+two-half component bench building. Bank128 write-face is dormant until runtime write-to-dependent-read/go+1 guard qualifies; arithmetic-stubbed boundary proof is not full projection qualification.
- **TOK (`token`, `ds_native`):** DS LINK-2GB repaired using395existingPIC libraries; no cache rebuild. Real pad/link first-dispatch diagnostic authorized, cohort11/01 explicit. IMG2 five missing components restored/rebuilding, not all395. QW controlled hierarchy build4 active, no40frontend burst. HBMvh1 build4 active. Model-only +13XFIN/+2partial updates do not change issued words.
- **Wave (`wave_flow`):** all5 waves activated on pinned2c705 source, p35 HBM/ctlrq HEAD, fresh roots. Publishing/fixing exact stale holds/retries in class batches; preserve live spilled jobs. Advance a stable later cohort after current tick, do not chase every merge.
- **Shared repair (`hbm_forms`):** private repair-only port-hold mask prototype repairs814internal qout violations in one chunk vs thousands of port-padding iterations. Final TT/FF constraints must restore exactly (17digit snapshot); unchanged final signoff, no live-kit edits. Not yet adopted.
- **Fleet/integration (`fleet`, `merge`):** all6hosts active; cleanup recovered45GB from creator-released pristine aborted checkout plus approved manifest cleanup. No safe large unreferenced candidates remain. Shared ECO bundle/nested-output fix merged. Integration READY queue stays batched; TKM old reset branch still awaits missing mutant control.

## Current integration / where to look

Latest confirmed main **7eff5fd60d2**; current physical shared tags at a9afc0fdd8b: x-head/v-qc/s-kv/x-s81/ae-hbm; newer KV-onlyt-kv on c63e950d550. Every abbreviated tag has prefix `flow-20261106-`. Wave's active2c705 cohort is older by design; merged does not mean deployed.

Pending next merges: S81 opt-in IDX hard-child support/source (activation waits actualGEN/current view/PG-OBS event); +2BEATnorm metadata. Other READYs go through merge owner, preserve exact proof/scope.

Concrete job paths/PIDs and newest results: per-lane `## CODEX notes`, `CODEX-LOG.md`, `lanes/CODEX-*.md`, and `lanes/COORD-REVIEW-QUEUE.md` on intel2 `coord/state`. Historical lane index: `lanes/CODEX.md`. Do not copy historical journals into this summary.

## OWNER? / handback

Two nonblocking questions are logged in CODEX-LOG: permission to migrate predecessor's exact unstarted192GB svc_lo proof waiter; permission for manifest moves of inactive superseded attempts protected only by terminal metadata. Defaults retain waiter and existing cleanup guards. Keep other work moving.

On explicit Claude-reset notice: park safely, append per-lane branches/SHAs/jobs/results/open failures/questions to CODEX-LOG, reply exactly `HANDOFF DONE`, stop.
