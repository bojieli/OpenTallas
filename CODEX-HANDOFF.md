# Codex handoff document (generated 2026-11-06 22:53 PST)

Standby: Claude is running; this is used only if Claude hits a usage limit.

Read ~/coord/CODEX-ROLE.md first: your role, the binding rules, and how to cover every task.

# OpenTallas — Claude -> Codex standby handoff

Updated by Claude COORD at 2026-11-06 21:19 PST. **Claude is running now. This file is only used if Claude hits a usage limit.** If you are reading it because the auto-switch started you, Claude's lanes have all stopped too (same account), so you own every scope below until told Claude is back.

Read first: CODEX-ROLE.md, AGENTS.md, ~/coord/METHODOLOGY.md, then the tail of `lanes/COORD-REVIEW-QUEUE.md` from 19:00 PST 11-06 (every RULING line there is binding).

## Progress (counter: `cd ~/coord && python3 -I tools/release_tree_plan.py --force && python3 -I tools/release_tree_render.py --summary`)

190 counted items at 21:05 (flat since 19:05):

| Die | Cores | Types |
|---|---:|---:|
| S81 | 54/58 | 9/205 |
| HEAD | 4/4 | 14/25 |
| QC | 24/26 | 0/119 |
| KV | 30/32 | 1/56 |
| HBM | 54/104 | 0/81 |

Die gates (BIND/GRT/STA/CLK) are not yet passed on any die. ETAs: non-HBM cores ~11-07, types ~11-11..13, HBM cores ~11-11/12, HBM types ~11-18/21, die-level ~11-14..16 (HBM ~11-21/24).

## OWNER rules added 11-06 (binding; older ones are in CODEX-ROLE / queue)

1. **"do not wait for them to merge before rebuild."** (21:2x) A READY fix is rebuilt AT ONCE from its branch head in its own flow tree on the least-loaded host (epyc5/epyc6 now). Signed results re-sign on the main flow tag after the merge (resign.py, PROVENANCE kind:resign) to count. Never hold relaunches for the merge train.
2. **Keep the fleet loaded.** At 21:1x the fleet was at 49% with 0 ot-run waiters. Target is >=0.85 x cores and >=4 waiters on every host.
2b. **"it is important to make conservative fixes and visually inspect the layout for all your subagents to remove congestion"** (21:5x).
   - Every failing core/type gets a conservative version in parallel:
     - registered faces with fanout <=8;
     - util <=0.40 for cores, <=0.35 for types;
     - signals <=M6;
     - feedthrough flops every <=450 um;
     - +1 PIN CYCLE for setup reach;
     - pipelined reset.
   - Every build has its density + GRT congestion + macro/pin PNGs viewed after place, GRT and route. Hotspots are removed structurally.
   - Lanes: HBM-CONS-1 (all open HBM cores, vK), QC-NLNK-RF (NL/NK vR), TYPE-CONS-1 (congestion + setup families, vC), ARCHIVE-1106B (disks >90%: epyc6 scratch2 37 GB).
2c. **"the visual layout checks should also find the fix obvious bad smells in physical design, for example pins on opposite sides, congestions in pins, too narrow channels, long diverged clock paths, etc."** (22:0x). Every place/GRT/route view runs a 10-smell checklist and fixes each smell structurally before the next stage:
   1. pins on opposite sides;
   2. pin clumps (>50% pin-layer track use);
   3. narrow channels;
   4. long or diverged clock paths, clock over macros;
   5. single-driver fanout spread >100 um;
   6. crossing or doubling-back data flow;
   7. logic far from its pins;
   8. density >0.7 next to empty areas;
   9. macros blocking the pin edge or clock entry;
   10. feedthroughs with no flop or repeater within 450 um.

   Posts carry "SMELLS: <list or none> [CHECKED png]". KW-FIX-24 is building an automatic smells.json plus renders per kit run, advisory, which lanes act on. Full text: job tmp core_lane_rules.md sections 21:5x and 22:0x. Codex: apply the same to every build you touch.
3. **Types safe by construction, all 5 dies** (TYPE-SAFE). Wiring and hold are fixed in the generator, not by rounds of patches:
   - track-budget corridors;
   - clock follows data (per-port tap windows, the TAPWIN-PORT SDC);
   - subtree_balance.tcl and ft_spread.py are default-on;
   - midpoint lockup latch `clock.ft_hop_lockup` is used only where a per-port rebuild still fails.
4. **Archive closed, delete non-closed** (ARCHIVE-1106 DONE). Signed results are archived to AGIdock `/archive/opentallas-signed-1106/<host>/<path>`, and a stub is kept on the host (signoff + PROVENANCE + final views + ARCHIVED.json). The key ~/.ssh/agidock_ot is on localhost only.
   - Never delete a stub.
   - Never delete kit_wave.json paths or asbuilt paths.
5. Standing rules:
   - safe forms, not retries;
   - two strikes, then RE-FORM (<=150k cells, util <=0.45, registered faces);
   - PIN CYCLES are cheap;
   - vA/vB built in parallel, first to sign off wins;
   - only sign-off blocks (TT setup >= 0, FF hold >= 0, DRV/DRC 0, LEC EQUIVALENT);
   - io-only hold counts as NEEDS_PARENT;
   - late-stage ECO is OK;
   - batch fixes by class;
   - owner questions in plain text with a default;
   - say "signed off".

5b. **epyc5 + epyc6 KEPT** (OWNER 22:5x: "keep both hosts. pause the deletion and move the workload from the waitlist to it."). No termination; the Cherry DELETE approval is withdrawn. Root floor 150 GB on epyc2/epyc4 (OWNER "use 150GB for floor decisions"); INV_HEADROOM_GB 32 on epyc4/5/6. Lanes: REBAL-1 (waiters to epyc5/6), AUTOCLEAN-1 (cleanup after each job), MONITOR-FIX.

## main and merge train

main = `239726a28c` (21:41, re-read the queue for the train). Merge lane ROOT-MERGE-46 takes merges on intel2 central `/home/ubuntu/OpenTallas`, using the merge lock and a plain merge plus tests. Approved order, none landed yet:

1. srcready b5710c267d
2. qcbatch 9976373442 (27 QC types, relay_resite_crossing default ON)
3. romqsplit c34808abe5 + framepairs 1152282347 (S81 rom_q halves count after this)
4. colst aa27610ffa
5. ftcorr f301811b71
6. type-safe-2 e23c27ec97
7. kv-fdicdc 82ac69b35d
8. PART 51 5e5e75c6dd, PART 52 7f9bb27ea2
9. centry-m5only 27427d7af5
10. kv-iocor 26fc32ca, then kv-slgland d725b196f4
11. KW-FIX-24 fixes:
    - restagehyst 7adf9c470d
    - lecunit 2ce49bbe04
    - leafrep a8fae7f643
    - pinband 1b7ce20e62 is HELD until its moves are confirmed on the 0.192 um grid
12. fgctx cc852ad06c
13. ONE flow-tag cut for all dies, then AUTO-RESIGN.

Also pre-approved: the HBM rest_1c spipe1 plan event, on its READY.

## Fleet

ot-run is on intel2: `~/.local/bin/ot-run --status`. Hosts: epyc2, epyc4 (256T), epyc5, epyc6, intel1, intel2 (= localhost in ot-run).

At 21:1x:
- epyc5 and epyc6 were ~30% loaded.
- epyc6 scratch2 is tight (~110 GB free).
- No heavy jobs on the owner laptop/localhost.
- Kill exact PIDs only; never pkill -f.

## Live lanes at handoff (Claude subagents; they stop with Claude — pick up their scope)

Each lane posts to lanes/COORD-REVIEW-QUEUE.md; its last STATE line there has paths and the next step.

- **ROOT-MERGE-46:** runs the merge train above (tests were at epyc4 /tmp/rm46_b15).
- **KW-FIX-24:** kit-wave class fixes (above).
  - At 21:1x it was told to run a pre-merge wave from the branch heads on epyc5/epyc6.
  - QC 27 first, then KV slgland 35, then S81 grt-overflow/post-cts-hold rows.
- **TYPE-SAFE-2:** structural type forms.
  - Canaries: S81 t14/t26 tsA/tsB, HBM q_spb2 vB.
  - Widen to ~77 grt-overflow/post-cts-hold rows on epyc5/epyc6.
- **S81-SSTN-HOLD-1:** 14 slice_station FAILs were stale pre-TAPWIN-PORT kits.
  - vP SDC-only re-kits count via resign on cl-s81.
  - t14/t26 vP ECOs on output-port hold.
- **DIE-S81-72 (S81 die owner):**
  - 16 stale rows;
  - leaf batch 2: t54 PIN CYCLES +1, t69 u_vs core move, t57 2-tap move;
  - rom_q halves (hw re-signed at epyc5 /srv/opentallas-scratch2/claude/s81-romq-b5/hw_x8_resign_at).
- **S81 core lanes:**
  - S81-ENGRR-B6 eng_rr_e: vC and vE (vE −97.9 ps on u_xq.u_aq.s0_x); ECO line closed.
  - S81-IDX-B5 idx_tx: vG/vH.
  - S81-BKSEL-RF6 bksel: vD-ECO/vE.
  - S81-RCK-3: serdes PHY pilots.
  - S81-T51-RECUT: register re-cut, in DRT.
- **DIE-QC-85 (QC die owner):**
  - su_l0/SU2/FE/fw rebuild from qcbatch head (START4 fix);
  - coll_ftm ECO pass 3 on epyc5 (pass 2: TT −13.73 ps, slew fail).
- **QC-A0C-B6:** QC NL/NK forms and ECOs.
- **DIE-KV-84 (KV die owner):**
  - KV slgland/iocor/fdicdc rows from branch heads;
  - KV die-kv-61 bind/ is lost and must be regenerated if needed.
- **KV-ING-6:** ingest i2 DRV ECO (intel1 /srv/opentallas-scratch2/claude/kving4/vE_eco/i2 is protected).
- **DIE-HEAD-76:** 7 stale rows relaunched at 20:47, hd_spn vC route.
- **DIE-HBM-82 (HBM die owner):**
  - 21 stale rows;
  - svgr_bk (B) FIFO/bank split, plus probes vPW45/vPW60;
  - svgr_own RF3 registered lane selects.
- **HBM form lanes:**
  - HBM-FORM-TIMING-13: rest_1c PIN CYCLES +1, vC/vD.
  - HBM-FORM-SPLIT-14 (+ SUX, OPSB sub-lanes): split forms.
  - Also live: B128 vA2 with LEAFSLEW, q3_edge_link, flc_eco1, epyc6 HBM core batch, d44v PART 40, rx_bm3_rest + svgr_top RE-FORM.

## Hourly loop (what Claude runs; keep it running)

- LOOP-GAP check at :00/:20/:40:
  - rule on every READY/ASK older than 30 min that has no [COORD] reply;
  - restart dead lanes whose scope is still open;
  - grep the kit-wave log for 'KIT-WAVE failed';
  - make sure ot-run has waiters on every host.
- HOURLY:
  - run the counter and add a lanes/SIGN-RATE.tsv row;
  - run `python3 -I tools/failure_breakdown.py` and paste it into the RELEASE_TREE.md BREAKDOWN block, plus line 3;
  - view 2 GEOM renders;
  - add a HANDOFF.md line;
  - commit with `timeout 280 ~/coord/bin/coord-commit.sh "msg" files` after `git fetch -q origin coord/state && git reset -q --keep origin/coord/state`.
- Relaunch FAIL rows older than the last class fix at once, from the branch head if it is not merged yet.

## Never

- Never print keys.
- Never touch ~/.claude, /home/ubuntu/closed_archive, existing /archive dirs (except new writes under opentallas-signed-1106), or owner VMs.
- Never run git in localhost /home/ubuntu/OpenTallas.
- Never use git add -A, force-push or stash.
- Cherry API is read-only.
- Deletions need a manifest first and the PROTECTED union. Skip .keep, live mounts, mtime <6 h and locked worktrees.

## Handback

When told Claude is back:
- park new launches and keep healthy jobs running;
- append `## Handoff to Claude <date time>` in CODEX-LOG.md with per-lane state (paths, running units, next step);
- reply HANDOFF DONE.

## Latest handoff milestones

- 2026-11-06 17:41 PST COORD hourly: count 187 (+1 HBM TX FF); 3 re-signs pending count; main idle since 16:01 -> ROOT-MERGE-46 told to land 8 approvals; RULINGS 17:4x (S81 ft re-site class, QC pin-under-PG class, HBM svgr M6 obs conditional); epyc6 21 GB REFUSED, move running.
- 2026-11-06 18:44 PST COORD hourly: count 189 (+2); OWNER rules 18:5x (types safe by construction all 5 dies -> TYPE-SAFE-1; archive closed to AGIdock + delete non-closed -> ARCHIVE-1106/PRUNE-1125; safe forms now on far-off cores); ETA table in RELEASE_TREE line 3; fleet 2/3 loaded -> KW-FIX-24 ba
- 2026-11-06 19:40 PST COORD hourly: count 190 (+1 HBM pipe_1c). rom_q hw half local SIGNED, re-sign ~21:05. TYPE-SAFE-1 step 1 in (clump not corridor; hold = tap window, midpoint latch). Rulings 19:0x/19:2x posted. Fleet underloaded on epyc4/5/6 -> KW-FIX-24 relaunch. GEOM: opsb p41 macro grid clea
- 2026-11-06 20:40 PST COORD hourly: count 190 flat. S81 station rows stale (pre-TAPWIN-PORT) -> rebuild batch + all-die stale sweep; DIE-S81-72 + TYPE-SAFE-2 started; KV land_r8 restore; failure label SETUP-AT-GRT live. GEOM: QC sul1 child landing kits sane (opposite-face pins); QC su2 channel lane
- 2026-11-06 21:40 PST COORD hourly: count 190 flat (main b37de6e708; merge train has not landed). OWNER rules: 21:2x rebuild from branch heads without waiting for merges; 21:5x conservative versions in parallel + visual check; 22:0x 10-smell checklist (all in CODEX-HANDOFF-STATUS + lanes/_CORE_LANE

CODEX: 2026-11-06 22:10 PST temporary takeover STOPPED; no new project changes/jobs/merges. Five new temporary worktrees removed per user; live fleet/source preserved. Full handback in CODEX-LOG.md. Main239726a28ca unchanged.
2026-11-06 22:32 COORD hourly: count 190 flat; lanes restarted after limit (lanes/_RESTART_1106.md); OWNER 22:3x drain epyc5+epyc6, terminate about 06:37 11-07, RETIRE-EPYC56 copies closed records.

For live jobs and new results, read the active lane files and lanes/COORD-REVIEW-QUEUE.md on intel2. Historical lane contents are intentionally omitted from this handoff.

