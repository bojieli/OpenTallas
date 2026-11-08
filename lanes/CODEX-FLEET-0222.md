# Fleet takeover 02:22

Updated 2026-11-08 02:24 PST. CODEX took over fleet/disks/queues/autoclean/monitor collection. No new cleanup, deletion, admission edit, job cancellation or chain restart.

## CODEX notes

All six hosts reachable by SSH. Commands run on actual hub via `ssh intel2`; local `ubuntu` ~/.local/bin/ot-run is stale (Nov1 three-host inventory), not an actual fleet outage.

Actual hub status 02:24: E2 admit12GB load182/128 waiters1; I1 admit226 load167/112 waiters2; I2 admit410 load80/112 waiters0; E4 admit48 load138/256 waiters3; E5 admit-8 load60/128 waiters11; E6 admit219 load26/128 waiters0. Actual unit counts:56/51/36/41/58/24.

|Host|Root free GB|Scratch2 free GB|Work guidance|
|---|---:|---:|---|
|epyc2|263|138|Memory-bound now; preserve admitted work|
|intel1|145|392|Root 5GB below150 floor; scratch2 only|
|intel2|174|302|Existing wave admitted jobs; no fresh clone on hub|
|epyc4|265|577 at02:24|Flagged cleanup progressing; scratch2 good|
|epyc5|153|236|Memory-bound;11 waiters; no new forced admission|
|epyc6|119|86|Below100 gen floor; memory-heavy disk-light LEC/STA/re-sign per01:00 ruling|

AUTOCLEAN-9: main landed tool835f84c0 and --queuename-skip-trim-c already installed on I1/I2/E2/E4/E5. E4 old tick ended02:15:39; detached flagged successor already started02:15:49 PID3016312, controls PASS02:23:39, active. Watcher did not start it. E2 flagged PID507858, I1 PID3311666, I2 PID2870741 still in healthy wt-reaper tail after successful manifests. E5 tick exited0 at02:18:06 (14.1GB peak); E6 previous tick exited0 at01:37:26 (649MB peak). Timers intact.

Collected manifests: I2 AUTOCLEAN-auto-intel2-20261108-020306.tsv; I1 ...intel1-20261108-021403.tsv; E2 ...epyc2-20261108-021434.tsv; E5 ...epyc5-20261108-101227.tsv; E4 next pending under ~/.local/state/ot-autoclean-auto/manifests. Last posted freed I2 165.45GB/I1 98.34GB/E2 73.07GB/E5 119.44GB; no new claimed totals before readback. Known root-owned cleanup errors I1 three rows7.7GB/E5 two rows0.8GB remain; permission cause, no retry/chmod/delete by watcher.

QUEUE-BAL-1 01:09 PARKED:35.1GB freed previously; .keep/signed/queue-name protections retained; no unstarted waiter restarted by Codex. E6 regained109GB then fell86GB due active output; do not assume old disk reading. Existing unpinned jobs re-place120s naturally. Wave lead advised exact headroom and memory-heavy E6 scope.

Next: collect E4 flagged manifest, monitor floors and new OOMs, report exact affected lane; keep protections and all healthy jobs. OWNER? none new; existing floor shortfalls are handled by placement guidance and standing authorized timers, no new deletion authority assumed.

## Collected 02:29

E4 existing flagged trim completed02:25:19: classC240 rows400.90GB freed, ERROR2 rows0.76GB both permission denied (hnx_vms_bank_q0_faces vecd4ae_wB and hbm-gaps-3/txh0), recheck0 and no ALERT; manifest ~/.local/state/ot-autoclean-auto/manifests/AUTOCLEAN-auto-epyc4-20261108-102519.tsv. Root425GB/S2 680GB; no watcher delete or retry.

All six kernel journals last45min: no production OOM. E2 two01:54 1GB-memory-cap OOMs were intentional rm48 tip/base tests allocating bytearray2GB, not lane jobs.

QC old a10 sle_su_l1__clc6d66f5b exit143 diagnosed exactly: hub WATCHDOG.log917 / WATCHDOG.txt and E4 unit2546337-1794124835 agree standing watchdog superseded-stop02:13, actual systemd STOP02:16:11, timeout SIGKILL docker2547304 at02:17:41. Why: attempt10 plan_current=no older than current live attempt12; idle0m legitimate any-age superseded rule, NOT false-hung. Current wave_jobs.judge reproduces. No source or runtime fix warranted; a12 untouched and QC notified.

Watchdog additionally02:13 stopped/relaunched Intel2 NK15m DRT once after6h05 no log. QC lead owns collecting .watchdog_relaunch_11080213.log; no extra restart by fleet.

## E5 waiter staging 02:34

Root authorized exact existing KW33 copy-then-link recipe; shared wave confirmed no move conflict. Selected current-plan t35a4 ENQUEUED job1e90f75102c6, existing unpinned frontend2249349; E5 memory-bound, cannot spill because named S3 target would land on I2 root. Copied complete gen (418 regular files,2,278,922,036B;0 deletions) from E5 to own Intel2 dedicated scratch2 /srv/opentallas-scratch2/claude/codex-fleet-0222/staged/t35a4/gen. No symlinks in source tree. After copy completion and target-absence/no target flow-container check, atomically symlinked original I2 scratch3 gen path to that dedicated-disk copy. Receipt own .../staged/t35a4/stage_receipt.json. Same sole frontend2249349 naturally re-places; no job launch, client edit, signal, source mutation or retry. Actual admission pending collection. Pinned waiters have no built-in live migration API; spill-handoff only collects an existing running spill. KV owner independently own-canceled e1 resign E5 waiter and admitted E6unit3117627; verified E5old310394 gone, no fleet signal.

2026-11-08 02:35 PST: T35a4 existingfrontend2249349 naturally rebalanced and ADMITTED Intel2oth-ubuntu-3746226-1794134103 at02:35:04,48GB/8t. Concrete queue migration, no duplicateproducer. S81lead notified to own later physicalresult. Actual I2pick351GB beforeadmission; samekitgen now dedicatedS2.

2026-11-08 02:39 PST: t35a4 preflightPASS/issues0, completed LEC EQUIVALENT28836/28836 reused; actualCAD active containerdpkit-ot_s81sl_leaf__t35-3748393 with route log advancing. Second same-recipe stage t11a15 job9d8ce85f41ec/frontend366249, currentplanENQUEUED, unpinned, completedLEC EQUIVALENT rc0; full418files2,330,980,821B copied to .../staged/t11a15/gen and original I2S3gen atomicallylinked after no-targetproducer check. No extra launcher/signal. Both ownstageparents have .keep containing exact live refs. I2S2=296GB aftercopies; secondadmission pending. Existing collector supports ran_on host, so no source-copyback needed.

2026-11-08 02:42 PST: t11a15 originalfrontend366249 ADMITTED I2oth-ubuntu-3851534-1794134365 at02:39, preflightPASS/issues0, completeownLEC reused, liveCTS. Both t35/t11 actualfreshstage CTS; numericoldrunlog tail is not DRT evidence. Third currentunstarted t24a14 job5dcef3bdb07a/frontend3064012 fullcopy inprogress, completedproofEQrc0; fourth QCstm2a7 job16955edce096/frontend635572 fullcopyinprogress with samechecks. Bothtargets remainunexposed untilcomplete/no-producercheck. No extra frontends, launches, signals, retries or policyedits.

2026-11-08 02:46 PST: Third existingwaiter t24a14 ADMITTED I2oth-ubuntu-3964651-1794134638; ownstage278files2,758,617,980B, preflightPASS/issues0 and completedLEC reused. Fourth QCstm2a7 fullcopy338files3,020,919,254B complete, sameI2S3gen alias exposed02:46 after no-producercheck; originalfrontend635572 re-places. No targetoverwrite/deletion or newfrontend. Source E5 remainsintact. S81four-preCADstation genrootresites are wavelead-owned, separate from mypostgenstaging; readonlyinspection found t22work1MB, no mutation. Unmodifiedot-mvlink woulddeletebackup, so I warned wave and didnotrun it.

2026-11-08 02:47 PST: Fourth QCstm2a7 originalfrontend635572 ADMITTED I2oth-ubuntu-4050584-1794134838; QClead notified to own nextstagegeometry andresults. Fifthcurrentunstarted QCsta2a10 slw_st_a_v2__clf4365a62 jobb23546015640/frontend847490 completeproofEQrc0/targetabsent/no sourceCAD, fullcopy underwaysame recipe. E6S2observed63GB at02:46, down23GBsince02:23; root/HBMnotified actualheadroom, no largeE6copies. E5root153GB actual vs reportedusable53=root153-floor100 (not diskcollapse); automaticcleanup466957active.

## Current disposition at 2026-11-08 02:54 PST

Four existing waiters have moved to intel2 through complete copies and the original frontends’ automatic re-placement:

| Item | Original frontend | Job | Admitted scope on intel2 |
|---|---:|---|---|
| S81 t35 a4 | 2249349 | 1e90f75102c6 | oth-ubuntu-3746226-1794134103 |
| S81 t11 a15 | 366249 | 9d8ce85f41ec | oth-ubuntu-3851534-1794134365 |
| S81 t24 cl648 a14 | 3064012 | 5dcef3bdb07a | oth-ubuntu-3964651-1794134638 |
| QC stm_v2 cl7b30 a7 | 635572 | 16955edce096 | oth-ubuntu-4050584-1794134838 |

Each has preflight PASS and its completed own LEC proof reused. These are progressing original jobs, not new attempts. Physical stage reviews and results belong to the S81/QC leads. Their complete gen trees are on intel2 under /srv/opentallas-scratch2/claude/codex-fleet-0222/staged/{t35a4,t11a15,t24a14,qcstm2a7}/gen, with exact original scratch3 gen aliases, receipts and .keep live references. No source deletion, signal, admission edit or extra frontend.

Fifth row QC sta_v2 a10 (job b23546015640, frontend847490): copy finished,422 files/4,851,801,760 bytes; held hidden while no host admitted48GB. At02:53 intel2 recovered to171GB admission; exact pick passed, current ENQUEUED state and completed EQ reconfirmed, then alias exposed. Actual admission pending collection. Sixth QC sta_v1 a9 already has an epyc4 spill copy with its .ot-run-spill-copy marker; no extra copy or marker edit. Epyc4 admission was0GB, so disk room alone cannot unblock it.

Finished retention subjects: KV e1_ds SIGNED/routed EQ29978 at epyc6 scratch2/claude/codex-kv-resign-0222/e1_ds; kit_e1 remains a live provenance dependency and is preserved. SVC token readlease obj at epyc6 scratch2/claude/codex-token-head-readlease-0222/obj is newly finished, under six-hour guard. No active archive chain was found; no chain restarted or manual deletion attempted. Existing cleanup timers continue.

2026-11-08 02:55 PST: Fifth migration admitted on intel2 as oth-ubuntu-54113-1794135315, same original frontend847490/job b23546015640. QC lead owns subsequent stage review and result. No sixth copy launched pending fresh host eligibility. Epyc4 existing sixth-row spill copy is marked .ot-run-spill-copy; marker retained and no bypass attempted.

2026-11-08 03:02 PST: Sixth complete copy is now exposed for the original client’s next re-place: QC sta1 a9, frontend4061896/job7d7668cfe3cd;390 files/4,965,698,816 bytes at intel2 scratch2/claude/codex-fleet-0222/staged/qcsta1a9/gen, original scratch3 gen alias, receipt and .keep. Latest eligibility before exposure: I2admits115GB/load82of112 versus I1admits105/load128of112; E4admits21, E5admits16, E6excluded from bulk at58GB scratch. No further copy planned.

Known monitoring limitation: real own staging paths lack /kit-wave/, so WATCHDOG job identity may fall back to Codex/report-only. Original autopilot jobs retain their identities and collect the actual ran_on host. S81/QC leads and root informed; healthy builds will not be moved/restarted to change this. Follow progress on the recorded scopes and logs.

Remaining pinned/raw E5 waiters: serdes t12a7 geometry PID252744/24GB; same kit raw async LEC PID3215044/48GB; current QC slw_hc2 cl6bc a10 raw LEC PID2177113/48GB; original KV e2 chain PID3843466/32GB. Wave rows current, not stale; no safe live-host migration API for these pinned/raw requests, and no signal sent. Owners notified.

## Six migrations complete — 2026-11-08 03:03 PST

| Item | Original frontend | Job | Actual intel2 scope |
|---|---:|---|---|
| S81 t35 a4 | 2249349 | 1e90f75102c6 | oth-ubuntu-3746226-1794134103 |
| S81 t11 a15 | 366249 | 9d8ce85f41ec | oth-ubuntu-3851534-1794134365 |
| S81 t24 cl648 a14 | 3064012 | 5dcef3bdb07a | oth-ubuntu-3964651-1794134638 |
| QC stm2 a7 | 635572 | 16955edce096 | oth-ubuntu-4050584-1794134838 |
| QC sta2 a10 | 847490 | b23546015640 | oth-ubuntu-54113-1794135315 |
| QC sta1 a9 | 4061896 | 7d7668cfe3cd | oth-ubuntu-201558-1794135687 |

All six admitted through the same original frontends and passed initial preflight with zero issues, reusing their completed own EQ proofs. No new attempt or frontend. Full copies and receipts remain protected under intel2 scratch2/claude/codex-fleet-0222/staged. No further bulk copy planned. Next: S81/QC leads collect stage geometry and results; fleet monitors E6’s approved single small KV CTS-only transfer (0.7GB input/~1GB growth, truthful5GB disk, unchanged50GB floor) and existing jobs.
