# OpenTallas — current Codex handoff

Updated 2026-11-06 03:02 PST. Current work only; historical evidence stays in lane files and the queue.

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

New results outside that cached census: KV ORDER qualified/count credit submitted; S81 t46 local signed; HBM brmw, injmw2 (TT+171.23/FF+.07, EQ18691) and N4rsq (TT+21.75/FF+.01, EQ13427) qualified. Do not recompute totals by adding these without checking existing census membership. IDX's signed child is not its unsigned parent. No die is released.

## Execution rules

- Follow `AGENTS.md`, `BRIEFING.md` and latest owner decisions. The intel2 coordination queue carries newer rulings than some historical methodology copies.
- Clock **833ps**, setup **TT**, hold **FF**, never SS for closure. Released owner12.24b/c uses **0ps setup uncertainty /25ps hold**, old60ps setup margin INFO. Do not change constraints during takeover.
- **Review before route:** render, actually inspect, record image/findings/verdict in `results/geom_review`. Check dataflow, faces, reach, density, macro channels, clocks and PG; fix bad geometry before routing.
- Failing cores get parallel targetedA and genuinely conservativeB (registered faces, <=150k functional cells, util<=.45, short reach/reset locality). Inspect actual generated config: explicit CLI settings previously lost to recipe defaults. Two structural strikes require a new form; few-endpoint residual ECO is permitted.
- RTL stays exact: smallest meaningful lockstep/formal plus mutant, kit LEC for adoption. Declare every added cycle to TOK/model. Preserve failed evidence. Only released sign-off qualifies; later owner policy accepts LOCAL_PASS_NEEDS_PARENT for local counting, not die release.
- **Hub=intel2. Localhost `/home/ubuntu/OpenTallas` is protected owner's checkout: no git there.** Own `codex/*` worktrees only. Heavy work via intel2 `ot-run`, measured RAM/disk admission. Preserve live jobs; do not duplicate them or kill another lane's jobs.
- New worktrees: use `--no-checkout` then narrow sparse paths before checkout. Tracked physical artifacts make a full checkout tens of GB; abandoned partial checkouts caused a fleet ENOSPC incident.
- Never edit scripts a live job reads. Fresh recovery copies and matched tool cohorts. No stash, force push, add-A, ours/theirs merges or deletion of others' unique work. Merge under intel2 lock, resolve in own branch, push and confirm HEAD==origin/main.
- Cleanup only approved exact scopes/manifests; preserve actual SIGNED/.keep/live/bind/unique state. Root floors: epyc2/4=500GB, intel=150GB, epyc5/6=100GB. Follow admission guards.

## Remaining 12 non-HBM cores (ledger basis)

| Core | Current action |
|---|---|
| S81 BKSEL Q | LEC66785EQ; retained GRT TT+146.25/FF-.8, private route continuation with actual PG6 pending. |
| S81 ENG RR E | Internal repair closes with ~1.4k buffers vs failed25k baseline; full parent IO still -148.38. Corrected continuation active. |
| S81 IDX TX | Child SIGNED TT+4.48/FF+.13/EQ5385; parent K10 rebuild with fixed hard-child generation/PG6 active. |
| S81 COLL E/W | Tall form rejected for parent fit. Original-footprint PG6/M6 canary GRT0, actual rails/vias; compact E/W builds active on epyc2. |
| S81 ROM Q | East TT+24.69/FF-22.28; west TT-22.79/FF-57.58, both DRC0. Late ECOs active; parent needs glue rows around exact-fit halves. |
| QC NK | Routed proof closed36818EQ. Long-leg repeater repair hit epyc4 ENOSPC during DRT; retained GRT recovered to epyc6 for resume. |
| QC NL | CE-preserving correction proved41990EQ; physical ECO active, three M6 PG shorts remain. |
| KV ORDER | Qualified TT+8.66/FF+4.48/DRC0; all proof complete; count credit submitted. |
| KV PEER | Actual .40/M7 reset/locality A/B active; measured29.8GiB peak,32GB admission. |
| KV PROMPT | Old B TT-72.86/FF-50.49; C2 physical completion hit ep4 ENOSPC, checkpoints salvaged for postwork resume elsewhere. |
| KV INGEST | r3 DRC0/EQ37991, TT-35.97/FF-3.40. C2 duplicates high-fanout phase control (34copies/528loads), no extra cycle; active. |

## Active lanes and next work

- **S81 (`s81`, `s81_core_results`, `s81_types`):** cores above; t13 macro resites and t51 conservative leaf forms active. t51 actual functional-cell growth exceeds150k: structural whole-payload split if current alternative cannot fix it. Legacy whole-payload FREG source/event merged; reset/control stages remain explicit.
- **HEAD/QC (`qc_head`, `head`, `residual`):** QC HC0 four real signed children and SLECTL split ready for coherent native adoption; union their independent sidecars. SU_l1 six station pilots launched after exact geometry/lockstep. HEAD actual clock association exposes severe real clock/FF hold problems (about-820ps), not a budget issue; real-view native transport/boot integration continues.
- **KV (`kv`, `order_peer`):** cores above; ring pilots active. Fresh SYS_C and PHY generation caught stale wrappers (101planned vs96emitted stages;3reset stations vs0): own prephysical workers stopped, canonical full bind regenerating. Fix shared fresh-kit preparation before releasing them. No physical-design strike for that tooling mismatch.
- **HBM (`hbm`, `gaps`, `wbq_safe`, `hbm_forms`, `vms_safe`, `bank128`):** q3 corrected SRAM width GRT0; qout repair-only hold pilot active; VMS remaining clock slew needs clock corridor fix. Bank128 A DRT0/ANT0, final timing pending; B and write-face trials active. Actual PG6 default-off capability ready (real rails/vias), parent M6 reservation/M7 landing still owed. WBQ p36 native split/profile/source guards ready; eight store helpers and body arithmetic repair active. q2nf_rest actual209669placed cells fails150k rule; geometry_forms owns two4-SRAM helper split with hbm/gaps.
- **HBM parent (`hbm_parent`, `kit_assembly`):** q_spb2 uses two real signed children, full reset context and mandatory internal stations; native field/control/face fixes before route. q_su21 measured fixed-face phase mismatch: preserve internal VI index2, separately retime external operand path4 under default-off variant, prove before new child qualification. Old signed views untouched.
- **HBM projection (`hbm_projection`):** actual arithmetic build progressing; do not restart. Owned-row option/compiler boundary proof passes, but arithmetic qualification pending. One shared owned-root type will latch global row from existing launch metadata rather than require24 rank-specific views; explicit23 remote inputs/calendar still required.
- **TOK (`token`, `ds_native`):** DS exact14station epoch biases merged dormant; scoped rebuilt candidate passes old epoch fault. Current KS diagnostic still has external HOST programming cut; do not call native boot. Default-off actual HOST frame queue/removal of force authorized. QW controlled build active; HBM top recovery reused86 interfaces and reduced frontend277GB to2.8GB, current top archive compiling. Historical cohort is not current G5.
- **Wave/shared (`wave_flow`, `kit_assembly`):** staged pinned cohorts, preserve live jobs. Shared source realization, sealed hard-child generation, full reset context/internal stations, actual PG publication, typed clocks, argv cache/parser and exact proof transfer merged. Mandatory canonical bind emission is the next construction fix.
- **Fleet (`fleet`):** disk incident on intel2/epyc4 interrupted jobs; preserve checkpoints, resume after measured headroom. Typed helper reclaimed its own abandoned50GB checkout; n4 reduced its own46GB source tree to120MB. Creator-released duplicate outputs only, no foreign/SIGNED/live cleanup. **Compare requested filesystem device against `/`, not just its pathname:** intel1 scratch3 and epyc2 scratch3 are ROOT-backed, contrary to earlier summaries. Direct OWNER root-heavy exception not located; only own unsupported root-backed jobs are being parked/re-homed. Verified epyc5/6 scratch2 are distinct from root. Scheduler status/admission misreports some root-backed capacity; fleet fixing it. No floor overrides.


## Integration / where to look

Latest confirmed main **7e11225c69a1582c2cef2d842ff7627a6b4d3dbf**; published tags ag-head/af-qc/ac-kv/ah-s81/as-hbm (prefix `flow-20261106-`). Merged source does not imply deployment or physical qualification. Merge worker owns central intel2 lock and source merges.

Merged since prior update: dormant real PG6, native source hash guard, dependency collector, optional LDCS2, HBM metadata-only cleanup, ninth QC ring export, selected hard-BB staging and geometry parse cache. All9 QC SLECTL rings qualified; controller remains ECO. HC0/SC five-type native union running; strict typed registered-hard-child face contract helper is active (no soft-D4 exemption). Pending source successors: hub-status must append default0 parameter; owned-root must preserve old12 positional parameters and exclude broad draft ancestry. Bank A coupled report looked positive but actual FF is-11.33/213 and DRV95/1; NOT SIGNED, M5 PG buried by M6 OBS also prevents parent use. RealPG6 A variant being prepared. WBQ p36 still requires actual native/profile/calendar/reset/PG qualification.


Concrete jobs, branches and latest evidence: active `lanes/CODEX-*.md`, `CODEX-LOG.md`, and `lanes/COORD-REVIEW-QUEUE.md` on intel2 `coord/state`. Historical lane index stays in `lanes/CODEX.md`; do not copy historical journals here.

## OWNER? / handback

Two nonblocking questions are logged in CODEX-LOG: permission to migrate predecessor's exact unstarted192GB svc_lo proof waiter; permission for manifest moves of inactive superseded attempts protected only by terminal metadata. Defaults retain waiter and existing cleanup guards. Keep other work moving.

On explicit Claude-reset notice: park safely, append per-lane branches/SHAs/jobs/results/open failures/questions to CODEX-LOG, reply exactly `HANDOFF DONE`, stop.
