# OpenTallas — current Codex handoff

Updated 2026-11-05 23:36 PST. This file is a current working summary; historical detail belongs in lane files and the coordination queue.

Claude stopped on the weekly usage limit. Reported reset: **2026-11-12 04:00 America/Los_Angeles**. Codex continues all lanes until explicitly told to hand back. Read `CODEX-ROLE.md`; record owner questions as plain text under OWNER? in `CODEX-LOG.md` and continue other work. Never open a blocking question dialog.

## Goal and current state

Complete DeepSeek ROM (S81 + HEAD), Qwen ROM (QC + KV), and the HBM accelerator. Each needs current physical views, whole-die routing/clock/STA, and token qualification. **No complete die release is established.** Component passes do not imply die closure.

Last recorded census: **167 signed cores/types, 2026-11-05 23:05 PST**. No new census was run for this rewrite.

| Die | Signed cores | Signed partition types | Main remaining work |
|---|---:|---:|---|
| S81 | 52/58 | 5/205 | Remaining cores; station/leaf and plan-source failures; parent routing/STA |
| HEAD | 4/4 | 12/25 | ctl RTL integration; clock-source tool recovery; remaining types and parent STA |
| QC | 18/20 | 0/119 | NK/NL closure, child ETMs/LEC, partition kits and die clock/routing |
| KV | 28/32 | 0/56 | HR ingest/prompt/order/peer; partition closure; token fault and parent STA |
| HBM | 48/101 | 0/81 | Core safe forms/splits, current plan/pin fixes, views and parent integration |

Counts above are the last census denominators; subsequent plan events can change the required core/type list.

## Rules and working locations

- Follow repository `AGENTS.md`, `BRIEFING.md`, the latest owner decisions in the coordination queue, and the binding methodology. Latest owner decisions supersede historical summaries.
- Clock stays **833 ps**. Setup at **TT**, hold at **FF**; never use SS for sign-off. Released owner policy 12.24b/c (queue 2026-10-31 00:56, 01:08, 01:19) uses **0 ps setup uncertainty / 25 ps hold uncertainty**, with the old 60 ps setup margin reported as information. Do not change constraints on takeover.
- Only the released sign-off result qualifies a block. Retain failures. Pre-build checks are advisory under later owner rulings; they do not turn a failed sign-off into a pass.
- **Review before route:** render and actually inspect each proposed plan/kit/core; record image path, findings and verdict in `results/geom_review`. Address bad geometry before route. Review placement/dataflow, pin faces, reach, density, macro channels, clock and PDN.
- Failing cores get parallel **vA targeted fix + vB safe form**: registered faces, <=150k cells, util <=0.45, short reach and controlled reset fanout. Two structural failures require a new form. Added cycles are allowed and must reach the token/model ledger. RTL changes need exact proof plus mutant control; adoption still requires kit LEC.
- Use own `codex/*` worktrees; never edit another agent's tree or scripts a live job reads. Heavy jobs go through **ot-run on intel2**. Preserve progressing jobs and collect their results before launching replacements. Never kill another lane's jobs.
- **Hub is intel2.** Localhost `/home/ubuntu/OpenTallas` is the owner's protected checkout; do not run git there. Integration uses the intel2 merge lock and plain merges, then push and confirm HEAD == origin/main. No `git add -A`, stash, force-push or ours/theirs merge shortcuts.
- Scratch/admission follows current ot-run policy. Root floors: epyc2/epyc4 500 GB; intel roots 150 GB; epyc5/6 100 GB. Follow the guard; do not bypass it. Preserve SIGNED, .keep, live jobs and unique work during cleanup.

## Active continuation and next steps

Codex workers are active for every scope below. Their concrete job paths/results are in the corresponding lane notes and reports; do not duplicate live runs.

| Scope / Codex worker | Collected result or failure | Next action |
|---|---|---|
| S81 / `s81` | ROMQ vA ECO exhausted; hw_vB GRT TT +138.54 / FF -1.62 ps. COLLE tall/wide probes still overflow (1041/2210). | hw_vB reviewed and resumed DRT on own copy; continue conservative COLLE forms and remaining core fixes. |
| S81 helper cores / `s81` | IDX vB TT -99.23 / FF -104.24; IDX vA child ECO TT +4.47 / FF +0.13 with one slew miss. BKSEL vBl LEC 66785/66785 EQ; GRT ongoing. ENGRR IO reference disagrees with measured insertion. | Target final IDX slew, collect BKSEL, correct ENGRR measured IO frame on private kit. |
| S81 plan / `s81` | gunit/seqhost sites merged. svc_lo t7 fit proof first OOM at 64 GB; 192 GB rerun is an existing epyc5 waiter, not a design strike. | Collect proof, then integrate fit/path event and release t7. Never duplicate the waiter blindly. |
| HEAD / `qc_head` | Several PASS-exit1 stops are a clock-source lookup exception already fixed by I184 psroot, not failed timing. ctlrq private LEC 59371/59371 EQ. | Recover/relaunch affected kits on current tools; integrate ctlrq, book ingress +1 cycle, collect serdes/type runs. |
| QC / `qc_head` | Shared LEC crashed on literal capture D (`KeyError '1'`); fix has 6 focused tests passing. NK vB4 GRT blocked by dont_touch ENA repeaters. NL vB routed TT -89.13 / FF -24.61, 3 DRC. | Integrate LEC fix; recover proofs; release only obstructive combinational ENA flags in private recovery kit; collect NK/NL and current child ETMs. |
| KV / `kv` | Ingest vA final ECO TT -33.21 / FF +2.09, DRC0. vB proof PASS with mutant caught. Prompt vB LEC 32050 EQ, DRT active. Peer A/B active. | Build proved ingest vB; collect prompt/order/peer and partition geometry trials; diagnose KV-08 witness RX path. |
| HBM die/GAPS / `hbm` | Wave plan was stale part11; current part34 extracted for operator. Rootctl A/B hold/DRV failures; bank128 canon ECO GRT overflow10; N4 FF -7.61 plus reset-role mismatch. | Apply p35 clock-pin separations and legal taller SerDes TX slot, review and build; continue safe forms/targeted repairs. |
| HBM forms / `hbm_forms` | h9b_vB ECO TT +0.83 / FF +0.35 DRC/DRV0, routed LEC/re-sign still required. brmw ECO SIGNED TT +1.53 / FF +0.90, routed LEC EQ; current-tag re-sign running. rb routed FF -9.11, otherwise clean. | Collect h9b/brmw current-tag qualification, finish rb hold ECO; collect all timing/congestion/split builds. |
| Token/model / `token` | HBM vh1 build3 terminal INFRA ENOSPC; successor build4 must be collected. KV ready-wait control also fails, so NOWAIT race alone is not the cause. | Diagnose KV mission/witness source; collect DS/QW/HBM benches; book every new pin cycle. HEAD ingress +1 edge is being recorded. |
| Kit-wave/flow / `wave_flow` | All 5 dies still used src_730 despite I188–I197 merges. Missing-source class fixed: ~80/121 rows had progressed. Stale spill markers obstructed roots. | Fresh roots configured; distribute current pinned source/tags to epyc5/6, current HBM part34, release pending batches, keep queues fed. |
| Fleet / `fleet` | PRUNE-1115 completed but was unreported: intel2 148.1 GB reclaimed, epyc4 ~456.5 GB removed/moved, intel1 ~35.3 GB moved. Some space consumed again. | Finish only already-approved remaining manifest rows; preserve evidence/live jobs; address epyc2/epyc4 root deficits through approved policy. |
| Integration / `merge` | I195 test suite has same 41 failures as prior baseline, no new IDs. ctlrq and shared LEC constant fix in integration batch. | Batch pushed, tags confirmed, operator notified. Integrate next approved class fix; no broad validation repeat without a new concern. |
| Shared residuals / `residual` | Autopilot labels explicit clock-source tool exceptions STRUCTURAL, suppressing proper infra recovery. | Fix narrowly by class, preserving actual timing FAIL classification; collect other unanswered READY/ASK and orphan work. |

## Current integration and follow-ups

- `claude/dh71-ctlrq-1105@4c71aa4289b`: root approved after scoped source/default review and token-cycle bookkeeping. Private proof covers held ctlx changes. Only hd_ctl behavior should change; raw plan keys stay unchanged.
- `codex/qc-lec-constant-1105@1fd5f3b4e3`: root approved, tiny shared tool fix with focused tests. No RTL or cycles.
- **Merged and pushed:** `875d41f5423` (ctlrq) and `eedc0185670` (LEC fix); HEAD == origin/main confirmed at `eedc0185670`. New tags on that commit: `flow-20261106-s-head`, `q-qc`, `n-kv`, `s-s81`, `x-hbm` (each with the same `flow-20261106-` prefix). Operator is refreshing sources. Focused integration tests: 12/12 PASS.
- HBM WBQ `claude/hbm-gaps-5-wbq-1105@12b6f8761b`: collect remaining exactness controls before adoption; vA/vB builds already live. GIN version adds +1 hbm_clk edge to g_v/g_d.
- HBM SerDes TX: root approved recommended taller 285.12 x 207.36 slot subject legal neighbor fit and image review, in p35 with clock-pin fixes. No new owner question needed.
- `codex/grt-tool-error-1105@067d834145e`: shared classifier fix READY, 15 targeted tests PASS. Recognizes the exact clock-source exception only with a PASS timing receipt; actual timing failures remain structural. Merged as `4d2e62a337e`.
- KV ORDER completed: routed TT +8.66 / FF +4.48, DRC0; remaining 16 proof cones discharged by BDD. COUNT-CREDIT addition pending; do not add it to 167 before the counter consumes the credit.
- Further pushed merges: `b95013ffc4e` lane1p vA source, `defc53fa878` WBQ HREG2/optional GIN1, `c6252e2eaf8` reset-copy naming fix, `2c7054fd3cd` HBM p35 pins/TX height. Main == origin/main confirmed at `2c7054fd3cd`.
- Latest shared tags on `c6252e2eaf8`: `flow-20261106-t-head`, `r-qc`, `o-kv`, `t-s81`; HBM-only `flow-20261106-z-hbm` on `2c7054fd3cd`. Wave source refresh is in progress; tags issued does not mean deployment complete.
- New generator precedence class: KV recipe defaults overrode explicit safe CLI util/layer settings. Merge worker owns generic fix; KV corrects actual peer/ingest kits. Inspect generated config, not launch flags.
- S81 COLLE same-placement M6 estimate reached overflow0 versus M5 overflow1041. Full build and parent M6 obstruction reservation remain.
- S81 svc_lo t7 fit/path additions are not ready until their existing proof completes.

## Live job anchors worth retaining

- S81 ROMQ hw_vB private DRT: epyc2 `/home/ubuntu/scratch-root/claude/codex-s81-1105/romq_hw_vB`; intel2 client PID 1879444, ot-run unit suffix1553856. Check the lane note for exact physical path.
- S81 svc_lo t7 proof: epyc5 `/srv/opentallas-scratch2/claude/die-s81-66-plan/locknq`; existing intel2 client4094614, 192 GB waiter, hosts pinned epyc5/6.
- HBM current extracted wave plan: intel2 `/srv/opentallas-scratch2/claude/codex-hbm-wave/d44v34`.
- HBM brmw current-tag re-sign: own `codex-hbm-forms-1105/resign/brmw`, intel2 client1895956. h9b corrected re-sign client1870751; rb hold ECO client1856903.
- QC NL routed LEC recovery: epyc6 `codex-qc-1105-ev/nl-vB-lec`, PID2694678.

## Where to find detail / owner questions

Latest evidence and handback state: `CODEX-LOG.md`, per-lane `## CODEX notes`, `lanes/CODEX-FLEET.md`, `lanes/CODEX-HBM-FORMS.md`, and `lanes/COORD-REVIEW-QUEUE.md` on **intel2 coord/state**. `lanes/CODEX.md` indexes historical lane files; a historical filename is not a new active task.

New nonblocking OWNER? items in `CODEX-LOG.md`: permission to migrate exact predecessor unstarted svc_lo proof waiter; and manifest-controlled moves of inactive superseded Codex attempts protected only by historical terminal-job references. Defaults retain the waiter and existing cleanup guards. Earlier questions remain in their logs; never invent approval or wait for an answer. On explicit Claude-reset notice, park safely, write per-lane handback (branches, SHAs, jobs, results, failures, questions), reply exactly `HANDOFF DONE`, and stop.
