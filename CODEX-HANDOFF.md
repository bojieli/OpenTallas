# Codex handoff — Claude COORD -> Codex (rewritten 2026-11-12 07:1x PST; replaces the 11-07 version)

> **Freshest state:** ~/coord/lanes/handoff/COORD-SNAPSHOT.md is regenerated every 15 min by cron (bin/coord_snapshot.py, no LLM): open READY/ASK, merges, lane handoff ages, ot-run status, KIT-WAVE, last 60 posts. Read it right after this file.


Read this when Claude is usage-limited. **OWNER ORDER 11-12:** Codex takes over ALL of Claude's lanes **directly**. That means:
- Continue in each lane's own worktree, branch, run dirs and watchers.
- Do NOT start new lanes, new codex/* worktrees or fresh rebuilds of work that is already running.
- Commit on the lane's existing branch, in the lane's worktree, with a `Codex:` line in the commit body.
- This overrides CODEX-ROLE.md step 4 (own worktree per lane) and the 11-07 watcher-mode limits, for work inside a lane's scope.

## 0. Start-up order (about 20 min)
1. Read `~/coord/lanes/handoff/*.md`, one file per lane. Each has: scope, worktree host:path, branch and sha, running jobs with how to check them, watchers, NEXT STEPS with decision rules, open READY/ASK, and gotchas. **These files are the primary handoff.** Section 3 below is the index plus COORD context.
2. Read the tail of `~/coord/lanes/COORD-REVIEW-QUEUE.md` from 11-12 04:00 PST. Every COORD RULING/REVIEW/LOOP-GAP line there is binding.
3. Read `~/coord/lanes/GEOM-REVIEW.md` (visual verdicts) and `lanes/VISUAL-QUEUE.tsv`.
4. Check what is still running before relaunching anything; builds survive a lane stopping. Use `~/.local/bin/ot-run --status` on intel2, plus `docker ps` and `ps` per host.
5. Then act as COORD and as every lane (section 2). Log one `CODEX:` line per milestone in `~/coord/HANDOFF.md`. Post to the queue as `[CODEX as <LANE>]`.

## 1. Binding rules (short; the full rules are in CODEX-ROLE.md, AGENTS.md and METHODOLOGY.md §12)
- **Keys and owner assets:** never print or commit keys. Cherry Servers writes need the owner. Never delete a host, never touch AGIdock authorized_keys or owner VMs, never touch known_hosts. ssh config and authorized_keys are append-only, with backups.
- **Git:**
  - Never run git inside `/home/ubuntu/OpenTallas` on intel2 or localhost; use the lane worktrees.
  - Never `add -A`, `stash`, force-push or `-X ours/theirs`.
  - main changes only through the merge lane, on a COORD-APPROVED sha.
- **~/coord:** change it only via `bash ~/coord/bin/coord-commit.sh "<msg>" <paths>`, then verify on origin/coord/state. Never `git reset` in ~/coord.
- **Processes:** kill exact PIDs or containers you or the lane own. Never pkill or killall. A lane on epyc7 ran `pkill -x python3` this week; never again.
- **Disk:**
  - No deletes outside the guarded tools.
  - Any move, dedupe or swap goes through `tools/ot_safe_swap.sh` (guard v2, bfcca667a9). It checks dev:inode and readlink, whole-tree deletability, and protected/queue/kitwave refs.
  - On 11-12 a self-symlink swap destroyed 7 source trees on epyc4.
  - Never touch `/home/ubuntu/closed_archive`, `/archive`, `~/.codex`, or `~/.claude` (except job tmp).
- **Owner rules in force:**
  - **Visual gate:**
    - After place, a type stops at WAIT-VISUAL until GEOM-REVIEW.md has GOOD or ISSUES-ACCEPT for that attempt.
    - Never relaunch a BAD form whose fingerprint is unchanged (WAIT-FORM).
  - **Families:** fix whole families, never per type. Reach problems (taps over the sink cap, hops over 405 um, reset reach) are fixed by REACH-FIX's deterministic tool at compose.
  - **Floorplans:** a hand top-level floorplan per die. Re-floor over signed types is allowed, with a batch re-sign.
  - **Clock gate:** routed pair setup >= 0 AND hold >= +10 ps.
  - **Core shapes:** frozen (move or rotate only), except for a declared exception.
  - **Slot fill:** below 0.15 gets an exception by default.
  - **Pre-approved by the owner:** outline or die growth, added cycles, perf loss and compiler changes.
  - **Wording:** say "signed off", never "signing".
  - **Owner questions:** plain-text `OWNER?` lines with a recommendation and a default. Never use a blocking dialog.
- **Heavy jobs:** only via ot-run, never directly on intel2 or localhost.
  - HBM is phase 2: a separate target, about 96 threads, lower priority.
  - epyc10 (Cherry 1062383, 2x7443) arrives around 11-14 and is reserved for phase-1 die-level runs.

## 2. Codex as COORD (what Claude did each hour)
- **LOOP-GAP (every ~20 min):**
  - Rule on every READY/ASK older than 30 min with no COORD reply.
  - Check every lane posted within 60 min; give an orphaned scope a successor by doing it yourself in that lane's worktree.
  - Check KIT-WAVE is launching: `grep KIT-WAVE ~/coord/autopilot/log.txt | tail`.
  - Check ot-run waiters and disk on every host.
- **HOURLY:**
  - Forced count: `cd ~/coord && python3 -I tools/release_tree_plan.py --force`. It takes more than 15 min, so run it detached.
  - Then `tools/release_tree_render.py --summary` and `tools/failure_breakdown.py`.
  - Add a row to `lanes/SIGN-RATE.tsv`.
  - View 2 GEOM renders and write verdicts in GEOM-REVIEW.md.
  - Update RELEASE_TREE.md line 3 and the BREAKDOWN block.
  - Add a HANDOFF.md line, then run coord-commit.
- **Fail monitor:** `bash /home/ubuntu/.claude/jobs/b7f906df/tmp/fail_watch2.sh` prints new FAIL rows. Batch failures by class, one class fix plus a batch relaunch.
- **Approvals:** approve READY shas to the merge lane as Claude did (tests named, scope sane, class not per-type). Do not change a plan of record on your own outside an approved die event.

## 3. Lanes (lane handoff file = `~/coord/lanes/handoff/<LANE>.md`)
| Lane | Scope | Where / state at 07:1x |
|---|---|---|
| ROOT-MERGE-60 | merge lane | Worktree epyc8 `/srv/opentallas-scratch2/claude/wt/rm60` (+ `rm60-main`), venv60. Train 60 tip `3d65e863df` (KV vN 52a724781a52 + qc-verify-gaps 2132a3e0d660/aac9d8eba287) passed the 59-style gate (main and tip both fail the same 43 tests); the wide list (`runwide60.sh`, `wide.list`) is running. Then: HOTFIX `claude/kv99-taps-path-1112@ae71bf887a8f` (taps.py missing Path import; main d767dc851b crashes G0/bind/gen with sink_bins). Then the train `cef99b3203` (land-override-stale) + `bfcca667a9` (guard v2) + `3d254c4a7973` (S81 ready12) + `33e70e1695` (CLAND-SLEW-1) + `a07f957bc5` (street-fixedface on 3cca0a68ed). Gate: the tip's failures must be a subset of main's on the 59-style list AND the wide list, `-n 16`, at most 2 suites at once, epyc8/9. |
| KW-FIX-46 | kit-wave class fixes, kit_wave.json | Items: PSPLIT sidecar (S81 gen_args `--clock-landing` to the split sidecar psplit2/psplit_all); WAIT-FORM hold_items (`ot_s81sl_leaf__*`, `ot_s81sl_kv_leaf__*`, KV `kv3_hg*`/`kv3_hgi*`, QC hcut1111/s25 old floor); S81 wave to ready12 minus 7 X-TIER; reaper keep list (KW-SRCGONE-1) so autoclean stops pruning referenced bind worktrees; intel1 as restage target once FLEET-2 posts ALLDONE; stale VISUAL-QUEUE rows; epyc4 rows needing qc_s27/hbm p18 go to epyc2/8/9. |
| GEOM-VIS-5 | visual gate reviewer | Answers every WAIT-VISUAL row; posts in GEOM-REVIEW.md. The die-level renders for KV vN / HEAD fix2 are in `lanes/die-proto-2/`. |
| HEAD-95 | HEAD die owner | West growth: decision by 08:15 between the fork-free fallback (street_rule legalize hd_lep0N, 0 growth, COORD prefers it) and forking hd_st_turn for nst1 (time box 09:00). HB4: eshim_tx SIGNED OFF; wshim_tx is drv-only (125 slew pins); wshim_rx DRV ECO + CLAND-SLEW-1. |
| DIE-KV-99 | KV die owner | vN2 (drawing due 11-13 12:00): hroot aspect exception, hgi_EN_0 cut, merge 21 types, W pocket (hg_wstreet.py), stations out of PHY, tap cap 1200. Sub-lanes items 3/5/7/8/9 running. Adopt VISLAYOUT3 F1 ft_street moves. Carry insertion balance. |
| DIE-S81-88 | S81 die owner | ready12b (insertion balance at compose + REACH-FIX +1 reg; leaf hand floorplan; no gear unless BUS-GEAR-2 is READY by 11-13 18:00). Also absorbs X-TIER-OTC, S81-LEAF-FLOOR, VL3-S81-*, LAND-RING-2. PSPLIT sidecars staged on every gen host. |
| DIE-QC-100 | QC die owner | s28 + HF-1c (claude/qc-s28-floorplan-1112@ea7be452d3, 3 GEOM-VIS-3 conditions). Sub-lanes: HF1C-LAND, S28-TAPS, taps+F+W fold, R1/R2 routes, visual-class forms. Must name the QC plan of record for DIE-PROTO-2. Must say whether coll_ft/fw forms are unchanged in s28 (if so they get ISSUES-ACCEPT). |
| REACH-FIX-2 | reach tool (`tools/die_plan/reach_fix.py`) | Worktree epyc7 `/srv/opentallas-scratch2/claude/wt/reach-fix-1`, claude/reach-fix-1112. New classes: RESET-WAVEFRONT-TAPS (re-derive taps/raw refs after a reset re-solve, by role) and INSERTION-BALANCE for all dies (die-agnostic, from the S81 ready12b method). |
| GEN-CLASS-1 | generator class fixes | Worktree intel2 `/srv/opentallas-scratch2/claude/wt/gen-class-1`. Next: SIDECAR-COVERAGE preflight, PLAN-SRC-MACRO preflight, classify the wshim_tx slew pins. |
| FLEET-2 | disk / admission / hosts | epyc4 restore of 4 trees into scratch2/claude/kw45-real (logs `~/f2_*.log`, each tree links only after verify). intel1 src pull (`intel1:~/f2_i1pull.log`, 121/125). epyc2: no more deletes; the f2-moved copies of ss29/codex-kv-phy-reset-1551 stay until a dry-run compare passes. |
| DIE-PROTO-2 | die GRT/STA prototypes | KV vN and HEAD fix2: GRT overflow 0, but the gates FAIL on landed clock damage (1031/1238 ps vs the 416.5 ps window) = insertion skew. Next: insertion-vs-distance fit, S81 ready12b, QC s28, HBM. |
| DIE-HBM-101 | all HBM, phase 2 | Cores in flight (topk D, fused_lane_c S3C, svgr_top, q2n2_vm_core, su31 G1e); hand floorplan v2 (M9 overflow = ft bands, not the spine); S00/S11 need a source tree that matches the plan macros. |
| BUS-GEAR-2 | S81 x-feed 2:1 gear | Worktree epyc7 `/srv/opentallas-scratch2/claude/wt/bus-gear-1`, branch claude/bus-gear-1-xint-1112. Steps: commit, EQ bench, +1 lane-cycle declaration, TOK-VERIFY, strict bind on ready12b, READY. |
| TOK-VERIFY-2 | token checks | Worktree intel1 `/srv/opentallas-scratch2/claude/wt/tok-verify-2`. bc62f30f4e READY; gear token check; post-train S81 token re-run. |
| VISLAYOUT2-QC | QC manual re-layout | coll_n reset-removal fix; vl2qc-fanout-cap 0080dc2d5c. |
| VISLAYOUT3-KVHEAD | KV/HEAD re-layout | F1/F1b stop after place (evidence for vN2); kv3_sys_SD_v1 SD-GROW goes to sign-off only if vN2 carries the +103.68 die width. |

## 4. State at 07:1x PST 11-12
- **Count:** 275 (05:39, flat). Cores 217: S81 61/64, HEAD 4/5, QC 31/31, KV 32/32, HBM 89/119. Types 58: S81 35/204, HEAD 19/26, QC 2/120, KV 1/56, HBM 1/81. No die gate has passed yet.
- **main:** `d767dc851b70`, which carries the taps.py regression; the hotfix is pending.
- **Root cause on all dies:** landed clock damage is INSERTION SKEW from the clock root (S81 0.25 ps/um, r=0.99), not hop distance. The fix is insertion balance at compose plus REACH-FIX +1 reg. Hand re-floors meant to shorten hops do not fix it; the HFP-S81-1 re-floor was withdrawn.
- **Fleet:**
  - epyc2 scratch2 has about 213 GB free with about 88 waiters.
  - epyc7 and epyc8 have about 80 waiters each, at or above nproc.
  - intel1 and epyc9 have free admit. intel1 becomes a wave host once its source pull finishes.
  - epyc5 is RETIRED.

## 5. Handing back to Claude
Park safely and let jobs run. Then:
- refresh every touched `lanes/handoff/<LANE>.md`;
- append `## Handoff to Claude <date time PST>` to CODEX-LOG.md (what you did per lane with shas, jobs started host:path/unit, results, open failures, OWNER? items);
- reply `HANDOFF DONE`.
