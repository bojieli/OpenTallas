# MERGE-QUEUE-1 handoff (successor, updated 2026-11-14 21:20 PST)

Task (OWNER 11-14): automatic merge queue for sha-pinned COORD approvals + kit wave on a pinned main tree. DONE, in operation.

## Live
- Queue: intel2 ot-merge-queue.timer (5 min). The service is TEMPORARILY pinned to the bootstrap copy ~/merge-queue/bin/ot-merge-queue
  (VERSION file), see the comment in ~/.config/systemd/user/ot-merge-queue.service. After 7fff3a1e0b1 lands, restore the ExecStart
  to the repo form (tools/fleet/systemd/ot-merge-queue.service: rt/current copy, bootstrap fallback) and daemon-reload.
- Log ~/merge-queue/log, state ~/merge-queue/state.json (re-queued false REDs listed under "requeued"); `ot-merge-queue status|parse`.
- Only COORD/OWNER-authored lines approve. Conditional rulings: proposed 'COORD APPROVED-IF:' (the queue ignores it).
- Gate: touched-path test selection under xdist; a new failure must also fail on a serial rerun of the branch and must not fail when the
  whole file runs on main (per-item base tree, same sparse set). Sparse: tools/, physical/common_flow, rtl/lib, rtl/common.
- Wave: autopilot.service drop-in zz-kw38-picker-runtime.conf + autopilot-aux.service run rt/current (backups ~/merge-queue/*.bak-mq1-1114).
  First tick on rt/76537ad08a5b 21:02-21:09 ok, run-items from rt/<sha>. kw38/rt is kept only for units still running from it.
- ot-tools-sync flips rt/current on hub + intel1 epyc2 epyc7 epyc8 epyc9 epyc10 after every push; ot-tools-drift.timer every 15 min.
- Per-host ot-run backends still differ from main (ADMIT-TUNE-1 owns them); drift lines list them.

## Open
- READY 7fff3a1e0b1 (whole-file baseline) waits for the COORD token.
- KIT-OPS-5 7d8520d56f32 (test_gpl_guard) and KITLOST 57ab6143d232 (test_wave_jobs) are real REDs, owned by their lanes.
- Local clone on rtx-pro: /home/ubuntu/wt/merge-queue-1-1114. Debug worktree intel2 mq1/wt/dbg-pga (can be removed).

## 11-14 21:54 update
- 2026-11-14 21:54 PST RESULT [MERGE-QUEUE-1 -> COORD; cc NEARMISS-FIX-1, NEARMISS-ECO, KIT-OPS-5] OWNER order done. claude/nearmiss-fix-1-1114 @966e3722ec6 was only in the hub clone ~/wt/nearmiss-fix-1, not on GitHub (21:45 tick: WAIT not fetchable). I pushed the sha to origin as that branch (new ref, no force); the 21:50 tick landed it first: MERGED main a88ea35f0fe -> 9adb525220f (GREEN, 10 tes
- 2026-11-14 21:54 PST READY [MERGE-QUEUE-1 -> MERGE-QUEUE (merge lane); cc COORD] branch claude/merge-queue-1-1114 head 868ecf1da24 (on GitHub): new tools/fleet/ot-src-refresh + test (3 pass), and an ot-merge-queue hook that runs the per-die refresh after each land and posts a STATE on CONFLICT/BUS
State: unit runs ot-merge-queue from rt/current; bootstrap ~/merge-queue/bin/ot-merge-queue = 7fff3a1e0b1; ~/merge-queue/bin/ot-src-refresh = 868ecf1da24 (manual: python3 -I ~/merge-queue/bin/ot-src-refresh refresh --from OLD --to NEW --dies qwen_compute,qwen_kvsys,s81,s81_head --apply). Open: approval of 868ecf1da24; ASK on catch-up apply.

## 11-15 00:39 update
- 2026-11-15 00:39 PST RESULT [MERGE-QUEUE-1 -> COORD; cc DIE-QC-103, HEAD-99, KV-102, WAVE-BALANCE-1] (1) QUEUE RUNNING AGAIN. 00:15-00:38 landed: kit-ops-6 ancestor-protect (50472807304, cf05598ef62), adoptguard 95e7edf8af6, plan-timing-audit (a5505562907, dea1a73bb3b5), s81-colgen-2 3cd0bf1b718, pg-pinband-1 6621b41723f, kit-ops-6 ca-chain 41835ce16ba, kit-ops-5 est5 df791a048f2, KV @426728e16ed -> main 973db049496. QC @a192501ee99b was already in main. wave-balance 7c617ca: MERGE-FAIL (orphan base, see 00:20 STATE); the rebased claude/wave-balance-1-1114-main @7766f2431cd needs a token. KV
Open: tokens for merge-queue-1 @850b1f53a81 and wave-balance-1-1114-main @7766f2431cd; QC gen_phys + HEAD check.py refresh conflicts with their owners; bootstrap ~/merge-queue/bin/ot-merge-queue = 7fff3a1e0b1 (fallback only), unit runs rt/current + drop-in src-hook.conf.

## 11-15 01:09 update
Gen breakage 00:26 fixed (cause: refresh wrote gen_host only; replicas mixed). Per-merge refresh OFF (drop-in MQ_SRC_HOOK=, now default empty in 453f6622a8d). Daily 06:00 ot-src-refresh.timer enabled on intel2 (needs 453f6622a8d on main; until then fails harmlessly). last good sha ~/merge-queue/src-refresh-last.json = 38ef0c93cdb. Replica sync scripts: /tmp/mq1-replica_sync.sh, /tmp/mq1-replica_add.sh on epyc9/epyc7 (one-off). Open: tokens for 453f6622a8d and wave-balance-1-1114-main @7766f2431cd; KIT-OPS-5 re-key of the 32 failed items; QC gen_phys + HEAD check.py 00:24 conflicts.

## 11-15 01:46 update
READY f9028d6ecf7 (daily all-copies + identical hashes + drift timer + put). Timers enabled on intel2: ot-src-refresh (06:00), ot-src-drift (:25); both run rt/current copy (need the sha on main). Code drift 0 on 4 dies after put of postcts_gate.tcl (+8 QC epyc2 files). QC 116 physical data files differ (flag only). Open: token for f9028d6ecf7, wave-balance-1-1114-main @7766f2431cd.

## 11-15 02:02 update
kit-ops-5-curplan-1114 @4c696027e0ef RED (branch alone fails test_kit_wave_composed_src refused_row: ROUTE-HELD vs FAIL/FLOW); posted to KIT-OPS-5. Waiter ~/merge-queue/curplan_wait.sh (pid 913804, log ~/merge-queue/curplan-wait.log) lands the next curplan token at once via tick --only and copies the MERGED/MERGE-FAIL line. Autopilot runs rt/current (no refresh needed). READY 26bd253bfdf (parser accepts the word branch).

## 11-15 02:42 update
19-token audit done (9 landed, 3 RED dly-spread/dly-spread-list/genbug-impl on kit byte-identity, 6 superseded marked REVOKED in state.json, curplan skipped). Parser fix 26bd253bfdf on main; daily refresh + drift timers now effective (rt/current has them). curplan waiter stopped.

## 2026-11-15 03:3x
- r64 genbug chain MERGED in order: fable-genbug 64d6a174f5d, genbug-impl def02ae19f6, dly-spread a7a198aeb79, dly-spread-list ad22c56cc3b (cherry-pick, 2 already in main).
- r65 s81-phypg-1 @e31f9ccd5c: was hub-only; fetched from hub + pushed to origin (no force); MERGED a55cbe3c34d.
- Open: 06:00 daily refresh (ot-src-refresh.timer) + hourly drift; QC gen_phys.py / HEAD check.py conflicts from 00:24 still with DIE-QC-103 / HEAD-99.

## 2026-11-15 04:0x
- ot-src-refresh installed at ~/.local/bin/ot-src-refresh on all 7 hosts. On intel2 it is a wrapper that runs rt/current's copy, falling back to ot-src-refresh.main. On the 6 gen hosts it is a wrapper that runs it on intel2 over ssh (kit_wave.json, ~/merge-queue and coord-commit live only there). Not on non-interactive PATH, so call it by full path.
- The 03:46 dry daily with the main tool failed the staged smoke on all 4 dies. Fix: branch claude/src-refresh-deps-1115 @33dde953101 (READY posted 04:0x): missing_deps() ADDs imported main modules; smoke allows odb/openroad. The dry run with the fix passes on every host.
- If it is not landed by 06:00, the daily swaps nothing (safe). After it lands, run it by hand: systemctl --user start ot-src-refresh.service on intel2 (only between waves).
- Die trees vs main list: intel2:/srv/opentallas-scratch2/claude/mq1/tmp/vsmain-0400.out (script vsmain.py beside it).

## 2026-11-15 06:1x
- put fix landed: claude/src-refresh-put-main-1115 @5dece1db8e7 -> main 782b88c3322. put reports gen host copy vs main; put --from-main writes main's version to the gen host and every replica. Cause of the KV gen_phys "SAME": put syncs the gen host copy and never read main.
- 06:00 daily APPLIED 38ef0c93cdb..782b88c3322 to every replica, identical after swap, smoke ok, no rollback:
  - QC: 6 hosts, ADD 4, MERGE 3, REPLACE 15.
  - KV: 6 hosts, ADD 6, MERGE 2, REPLACE 16 (+2 deps).
  - S81: 5 hosts, ADD 5, MERGE 3, REPLACE 16 (+1 dep).
  - HEAD: 3 hosts, ADD 11, MERGE 2, REPLACE 17 (+7 deps).
- Next daily: 11-16 06:00 (base 782b88c3322 in src-refresh-last.json). Drift check hourly at :25.

## 11-15 09:50 update (successor 2)
- Train since 08:00, all MERGED: core-bksel 4cb55d1bc58, mq-ready-gate a530ec0ae90, typemerge 10c9c1c2d55, stream-land f8702115908 (parallel gates, in-order land), rom-viamap a0402ec7083, taprows 0057d544543, oldplan-block ab284566664, kv-rawfix 6e938d93a48, leaf-t14-1115b 12f54cf1aec, wave-copyback 1faf0c24936. FAIL to lanes: flow-health a1992/5c0c (test_ot_run_direct Choose), epyc2-scratch3 (scratch_disk timeout), ca-band c9d1, kit-rtl-src-tree-1115-2 783923a5c86.
- READY claude/mq-ready-gate-skip-1115 @49b29925549 GATE main=358553fd3e6 pass=16/16 (skip settled READYs; fixes the live .strip() crash in the gate check). Needs COORD token.
- Hub (intel2 /home/ubuntu/OpenTallas) main stale at 22c217df54 + tmp/s81t14-main-fb7cf958; outside my rules, ASK to ROOT-MERGE-63/COORD (09:45 STATE).
- ot-src-refresh: put --from-main (782b88c3322) + missing_deps (ddb0624c3d4) on main, installed on all 7 hosts (gen hosts ssh-wrap to intel2). LOCAL branch claude/src-refresh-mergeguard-1115 (worktree /home/ubuntu/wt/merge-queue-1-1114, 2 unpushed WIP commits d320a4adc1b): closest-main-base 3-way merge + guard (clean merge that drops a main def/class/proc -> CONFLICT kept) + SMOKE attribute check + batch blob prefetch; 13 tests pass. Fleet dry run running on intel2: mq1/tmp/guard2-dry.out (ot-src-refresh.guard2). MUST land before the 11-16 06:00 daily (live daily still bases merges on the last-daily sha, which dropped full_area_hard_ip at 06:00 today). Next: squash the WIP commits, rebase on main, test, push, READY with GATE.
- Die trees: all 4 at the attribute-scan baseline; HEAD gen_phys HEAD-SERDES-SECONDARY hook re-inserted (stamp 20261115-170239).

## 11-15 12:00 update (successor 2)
- MERGED since 09:50: wave-copyback 1faf0c24936, mq-ready-gate-skip b89ba8df4f0 (fixes the live .strip() gate crash), epyc2-scratch3 6b4f2ff26a2 (I requeued it: the TIMEOUT was load only), kit-rtl-src-tree-1115-3 dd72c6d80e3 (783923a5c86 + mkdir fix).
- Awaiting canonical tokens (the parser misses r130/r132 forms; ASK 11:50): mq-gate-cmd @5f6c68b932d, mq-lane-clone @342a1b32b67 (or 1617cedd312), kv-pvgen @bb5381316de5, mq-approve-list @f2dd5c5e98d (the parser fix, with an 11:00 cutoff), src-refresh-mergeguard-1115b @b64e3a85ef3 (MUST land before 11-16 06:00).
- Lane mirror LIVE: intel2:/srv/opentallas-scratch2/git/OpenTallas.git, ot-git-mirror.timer (2 min), ~/.local/bin/ot-git-mirror; ot-lane-clone on all 7 hosts. Hourly ot-lane-audit.timer (:07) -> ~/merge-queue/bin/lane-remote-audit.sh posts the hub-origin clone count until 0 (log ~/merge-queue/lane-remote-audit.log).
- Hub-only claude/* refs: 694 refs (commits not on GitHub) pushing from the independent clone kw35/repo through the mirror (mq1/tmp/hubpush.sh, out hubpush.out, forward.log in the mirror; per-ref after the batch failed, ~10 s each). 1669 more names point at shas already on GitHub (not pushed). 65 DIFFER names: report only.
- Not on the queue yet: record check (READY stamp must match ~/merge-queue/gates/<sha>.json) after gate-cmd lands; auto front-of-train for flow fixes.
- Worktrees on rtx-pro: /home/ubuntu/wt/merge-queue-1-1114 (main clone), /home/ubuntu/wt/mq1-krst, /home/ubuntu/wt/mq1-e2s3 (both can be removed).

## 2026-11-15 12:12 PST update
- MERGED: src-refresh-mergeguard 5f7b1e7f56a, gate-cmd 7b0539de126, lane-clone 94682f1a447, approve-list c792e43916c. RED (lane-owned): kv-pvgen bb5381316de5, src-tree-manifest 4b3df8d01a8a.
- HUB-ONLY ref (COORD: leave it, no history rewrite): claude/cores-s81-1-wave-por-1112 @896c87c3e994 (GitHub refused, file too large).
- Lane remotes: ot-lane-fixall + hourly ot-lane-audit.timer (:07, ~/merge-queue/bin/lane-remote-audit.sh). 31 left: 3 busy (epyc7), 28 worktrees of gen-host ~/OpenTallas (moved/home__ubuntu__OpenTallas, origin hub:OpenTallas); ASK posted to fix those 4 checkouts.
- hubpush (694 refs, kw35/repo -> mirror) still running: mq1/tmp/hubpush.out, mirror forward.log.

## 2026-11-15 12:51 PST update
- r137 done: gen-host ~/OpenTallas origin -> mirror on intel1/epyc7/epyc9; epyc8 busy, retried hourly by ~/.local/bin/ot-lane-fixhome (called from lane-remote-audit.sh). PATH line at top of ~/.bashrc on 7 hosts (MQ1-LOCALBIN, backup .bashrc.bak-mq1-1115). ot-merge-queue wrapper (gate|known-red|status|parse) in ~/.local/bin on 7 hosts. MERGED: src-tree-manifest cdb8191563c, merge-census-1115-4 33b03c8ba37.

## 2026-11-15 14:25 PST update
- READY claude/mq-gate-deps-1115 @af5cfe9eb09 (gate sparse tree gets the sources the selected tests name; MISSING SOURCE -> INFRA). kv-pvgen-1115c @58c1bd939f8 regate with that code: intel2 mq1/tmp/kvpvgen-gate.out (copy omq-deps); gate-cmd runs one at a time (gate-cmd.lock).

## 2026-11-15 15:18 PST update
- Remote gates: /srv/opentallas-scratch2/claude/mq-gate/ot-gate-remote on epyc2+epyc9 (venv mq-gate/venv, clone slots slot0-7 of the lane mirror), driver intel2 mq1/tmp/rg.sh, outputs mq1/tmp/rg/*.out; GREEN records copied to ~/merge-queue/gates/. Usage: ot-run --mem 48 --threads 16 --hosts epyc2,epyc9 --dir /srv/opentallas-scratch2/claude/mq-gate -- bash /srv/opentallas-scratch2/claude/mq-gate/ot-gate-remote claude/<b>@<sha> 16
- Needs tokens: claude/mq-gate-deps-1115 @55adcc5c3f2 (gate-record landing, MQ_GATE_PAR, ot-gate-remote, missing-source rerun; drt0255 regates after it), claude/kitrtl-fail-1115 @cf4e05a04fc (GREEN, COORD pre-approved).
- Still running remote: kv-pvgen-1115c @58c1bd939f8, flow-health-1115b @954e9e33029 (both approved/queued). Hub tick 15:13 gating hold-release-on, qc-cb-gen @0784de12b28, noprog-grt, flow-health @954e, m8-grant.

## 2026-11-15 15:5x update (successor, r177/r178)
- MERGED kitrtl-fail @cf4e05a04fc -> 3813f569afe (15:35, landed first). MERGED mq-gate-deps @55adcc5c3f2 -> 85738b82470 (15:40).
  Gate record trust and the missing-source rerun are live on rt/current.
- The 15:41 tick took flow-health @954e (GREEN 15:53, landing), m8-grant, clksite-r4, s81-seam-rst-1115-2, drt0255 and pg-cell-keepout-tap.
  pg-cell-keepout-tap has a remote GREEN record (main e57480d51f6, 2/2).
- READY claude/mq-gate-deps-1115b @39560175da1 (not approved yet): up to 3 missing-source rounds, then the whole rtl/. ot-gate-remote takes OT_GATE_CODE.
  Remote copy of that code: epyc2 and epyc9 mq-gate/ot-merge-queue.bef8ec0a177.
  drt0255 is regating on the remote runner with it (mq1/tmp/rg/drt0255-pg-rows-1115-1.out).
- FABLE-FLOW-1600 rules (r178), not yet in code:
  - gate branches named in a hold release_on first;
  - one gate per sha (skip remote when the tick has a worktree for that sha);
  - gate a READY without a stamp yourself, never bounce it.
- Force-first script: mq1/tmp/first2.sh pattern (stop timer + service, tick --only, trap restarts timer).

## 2026-11-15 18:1x update
- r177/r178 train all MERGED (kitrtl 3813f569afe ... drt0255 78697599c68, then noprog-fix, qc-cb-gen ac68, gate-deps-1115b@3956 -> d35f4c5e46d).
  rt/current was checked equal on all 6 hosts (9afae4e98166, 16:3x). COORD: verify readlink on each host and post the sha after EVERY train.
- READY claude/mq-gate-deps-1115b @442f26021f2 (GATE main=8989ba7b175 pass=2/2), awaiting approval:
  - remote-runner tick gating, pregate instead of bounce, gate-tree reaper, mirror hub-only skip, record note.
  - After it lands, reset state ready_from to ready_from_saved (13902) under the flock. Bounces are OFF via ready_from=1e9 until then (mq1/tmp/noready.py).
- Ops done: gc.auto=0 / maintenance.auto=false on mq1/repo; playwright in the gate venvs (intel2, epyc2, epyc9); intel2 mirror hub-only.txt.
  The new ot-gate-remote (reaper) is deployed on epyc2 and epyc9.
- clksite-qc-snap @7b9953f2d73 MERGE-FAIL is a semantic conflict (TAP_PIN_SNAP default); the lane owns it.
- The mirror sync died every cycle on the cores-s81 forward until the fix lands; lanes can push to the mirror directly.

## CODEX takeover 2026-11-16 10:28 PST
- Direct queue takeover; no owner checkout writes, no new lane/clone. Source gates run once via admitted mq-gate epyc9; logs intel2 mq1/tmp/rg/*-1116.out; full-SHA GREEN records in ~/merge-queue/gates.
- Landed through main2259ce1358a: r313 count hosts; r314 KV tools272407d9f41 and HEAD DOREG67db0dbd; HEAD schema6a4646; QC packed-driver0551428; CONG advisory-only9961807; data_pack map-file322cf809; HCFE default-offa37b263; NOPROG advisory4877c82; current-source svc closure79ca679. Last confirmed full fleet sync main06c5e501a8fa at10:15; next sync after2259 train is automatic.
- Ready source gates for root: final token9ffad1bf706cdc385808689239094d9eadef44b4 GREEN4/4; native modern-only507a77c7149f01028419b23386c31d446fe80190 GREEN26/26; clockreachcda5a7251117e78fdf815f49563fe707c69b52ff GREEN51/51. No own live gates as of10:28.
- Immutable FAIL: nativeeb79c43046c33adb3938323e623e8a4370f8effa changed frozen legacy RUN_KIT bytes; corrected507 restores frozen literal/hash and changes modern runner only. Failed log retained native-eb79c43-1116.out. No unchanged rerun. Superseded tokendecfb gate GREEN but not for separate adoption afterfinal9ff.
- Historical merge failures inspected against current needs: old tap-clear intent already present indirectly; no current QC/KV gate needs old tap-snap or default LAND_RESERVE; old capped START experiment not current. No speculative replay. Active CONG clone and its untracked t8/t28 review drafts stay intact.

## CODEX continuation 2026-11-16 11:09 PST
- Queue landed through main63eb7038242; six-host runtime sync63eb70382420 succeeded10:58. Later train now active (picked11:05): toolskewd10df7b, tokeninputa67e055, QC data-packf2e64f6, clockchain ddf6d82 (carries c73/4aa3ebbc), future final-only PRDprecleanbe4e664. Main records and immutable logs remain the source of exact merge SHAs.
- Additional source gates actual GREEN, one admitted run per changed SHA: HEAD TT-PG replay8df7c2f65/65 (mergedmain6ce01001775; real2-net GUIDE_REPLAY_PASS separately collected by HEAD, no DRT/signoff claim); QC checker3db14d4 1/1 (mergedmain31cb5df330f); GENBUG bound-fastpathd7bebc0 60/60 (mergedmaine37cb718b58); sourceidentity5da9a87 131/131 (mergedmain63eb7038242). Prior failed nativeeb79 corrected by507a77c26/26 and mergedmain5959d7e42a0, frozen legacy bytes kept.
- New final source records pending root approval: token VMR benchd76cceb65caf3d064e771a643cbc10264de186cc GREEN2/2 main63eb7038242 (carries a67, component-only251edge proof owned by token lane); clock fixed-FT4aa339ad7819352bfffae2c793bb997a4aad6bc4 GREEN51/51 same main (distinct from old padding4aa3ebbc). All full-SHA records in ~/merge-queue/gates; logs mq1/tmp/rg/*-1116.out; no own live gate job11:09.
- Existing owners settled current failure relays: QC96c681d4b6/f6f8584378 (latter parser feedback on diagnostic text), HEAD8070467972, native48e5b3767e15. Native one-BUF reproducer diagnoses M7 clock planar usage outside M6 resource vector; exact current successor is native worker-owned, not the separate future PRDpreclean source change. No duplicate routes or arbitrary stops.

## CODEX continuation 2026-11-16 12:30 PST
- Queue landed source fixes through main205d355eea7 (HEAD3619); earlier compiler0ac ->31a3714a407, relative-map39523 ->746435db313, HEAD506b ->3289b7955f5, exact BK d8 ->080001b1124, thin IFN0 metadataa2 ->20b2923a8a6, resetd5 ->55af774a270. Runtime last confirmed20b2923; normal queue sync continues.
- Launch-critical final source GREEN4677b692c544627e9fed4def2ac933289f06dfde131/131 and ee39c902d0825b350b219d78e0e1806e06533007134/134 (main080001b,one baseline each). Never deploy supersededfb630: final4677 honors per-item kit_rtl override in failure context. Owners retain actual KV3/29S81 GEN follow-through.
- Other final source GREENs pending root approval: token6b9d2833f9ebb135a8bc1fd55654f84da2014f6b76/76; CONGb6a822df86fe0866d4b9fdbaecbc7fc69a0811bc165/165 (paired compiler0ac nowmerged; physical adoption separate); QC44868df838a11577adfe2bf02b7df99313ed11c66/6 (carries804 plus native SRAM registration); QC plannerdec8cc442acfcee01c5f3f85fd363db15188ef9e37/37; HEAD78895d749885b5b50303ec480d4c19cbdc41d66177/77 and1ef6fc4d571283ba6665b7daf806708adc7cb5142/2; GENBUG snapshot e2e31d8fc41db20c1676b89fa07c4ad33c9d739a2/2; optional snake fd9996e0104374edcd2121db6124a5d9abe0d7e691/91. Exact gate records canonical ~/merge-queue/gates; immutable logs mq1/tmp/rg.
- Serdes978 source gateGREEN57 but actual queue checkout INFRA pulled whole sibling results trees for shallow JSON records, then left empty index.lock after timeout. Checked no live holder/no git cwd in its queue WT; preserved stale lock as mq1/tmp/978eeface-index.lock-preserved-1116. No jobs cancelled. Narrow queue sourcefix1126d56e686221e1f29d000ded9619dc5ad5e938 on claude/mq-sparse-records-1116 GREEN2/2, only queue+test changes, exact-file sparse selection preserves directory dependencies. Root approval/runtime sync required; do not keep retrying old broad checkout.
- Sole own live gate is exact final Serdes followonad2ec50d51d24f3ade1e86c27a08211f6610d113 client791647, log serdes-ft-ad2ec50-1116.out; defaultoff FTstage0/cohort/BOOT3 model/corridor placement source only, no component proof repeats.
- Diagnosed QC baseline broad historical pin fixture test_full_sm_rf_service::test_pinned_sources_identical compares entire evolved model/FP add/mul to5250fe00a; all3 differ on main. SVC baseline test_svc_bound_without_native_helpers_passes (7known occurrences) assigned closure owner source/asset-order diagnosis, no component repeat.
- Inherited dev WT mutation ownership returned by sparse_checkout child. Current branch claude/mq-sparse-records-1116; thin artifact train claude/merge-queue-records-1116 retained. Original dirty state preserved WIPb1cbb5f3c2e5 + refs/preserve/mq1-dev-before-ifn0-1116 and mq1/tmp/preserve-dev-before-ifn0-1116.patch. Active CONG clone/drafts remain preserved.
