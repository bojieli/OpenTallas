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

2026-11-08 03:06 PST: Additional finished retention subjects recorded without deletion: I1 codex-head-lep-0222/probe (~414MB, source3_2.odb and reserved.odb plus review evidence), tiny old E5 codex-head-lep-0222 probe/source tree. Both fresh<6h. Live successor I1 .../kit/hd_lep0N_vF_reserve scope572991 stays protected.

Approved E6 one-screen case owned by KV hubs: /srv/opentallas-scratch2/claude/codex-kv-hubs-0222/capture-screen,617MB input via capture-pilot/input/3_place.odb, expected~1GB CTS output, --disk5 and unchanged50GB guard. Earlier E4 waiter failed before CTS on missing macro_cts_cluster.tcl; owner is fixing the full helper set before the E6 launch. No live old payload, no fleet retry or additional form.

## Failure diagnosis 2026-11-08 03:09 PST

SVC numerical miter compile, epyc6 scope oth-ubuntu-3156689-1794134077: confirmed MEMCG OOM at03:06:00 PST, not inferred from exit143. Kernel memory usage=limit67,108,864kB (64GiB), swap0, CONSTRAINT_MEMCG; victim cc1plus PID3634650, anon RSS66,556,880kB (~63.5GiB), total VM66,761,696kB. Unit result oom-kill03:06:05, peak64G. No earlyoom or watchdog action. One compiler process consumed almost the whole cap; reducing parallelism alone cannot solve that. Root and SVC owner informed; E4 checkpoint resume requires larger measured reservation or compiler/output splitting. Source and objects untouched.

KV Eo screen E6 scope3680794-1794135983 exited before clock_tree_synthesis on missing RESULTS_DIR after the earlier missing macro_cts_cluster.tcl support issue. Owner retained logs, supplied screen_results, and handles same-form support-only requeue with unchanged guard/disk. Fleet requested a combined environment/transitive-helper check before the next call; no extra CTS attempt by fleet.

## SVC checkpoint recovery — 2026-11-08 03:17 PST

At RTL child’s request, completed the interrupted E6→I1 checkpoint transfer with sparse/compressed resumable rsync, no deletes. No old tar/rsync writer was active on the I1 target. Source E6 .../codex-svc-rtl-0222/miter2/obj stayed untouched. Destination I1 /srv/opentallas-scratch2/claude/codex-svc-rtl-0222/miter_resume/obj now has all2376 regular files,2,670,521,109 bytes;489 missing/incomplete files were transferred (733MB logical,39MB wire), exit0 at03:16:09. Explicit COPY COMPLETE sent to child before its own96GiB/J1/effective-O0 checkpoint compile; fleet started no build or Verilation. Exact10-line kernel+unit excerpt retained at destination infra_memory/epyc6_3156689_memcg_20261108_030600.log.

## Continued support — 2026-11-08 03:31 PST

RCK live alternates dependency registered on I1 through existing ~/.local/state/wt-reaper/protect.d/codex-fleet-0222-rck-alternates.txt: /srv/opentallas-scratch2/claude/s81-rck-10/repo/.git/objects and /srv/opentallas-scratch2/claude/codex-s81-rck-0222/work. Both retention tools read that registry; autoclean already guards alternates targets. No source/repository mutation or deletion. RCK owner informed.

SVC child’s I1 96GB checkpoint resume was still queued while I2 had301GB admission/load75of112. At its request, staged the completed I1 miter_resume to the same path on I2, preserving I1. Target absent/no writer; rsync copied2379 regular files/2,670,523,220 bytes (100MB wire), exit0/0deletes at03:30:56. Explicit copy-complete sent; child checks original I1 admission before its own cancellation/rehome decision. Fleet started no compiler or Verilation and signaled no client.

HBM Q2NF small pilot won admission on I1 while staging was considered; owner kept that healthy job and started no duplicate on I2. Its failed rsync SSH-n attempt transferred no bytes; empty own target dirs are fresh and retained.

E6 KV screen executed CTS+legalization, then failed diagnostic capture-pin lookup beforeDBwrite; manual library glob also omitted uncompressedSEQ, so no valid timing result. Owner has held the form and started no further run pending root ruling. Output remained89MB, scratch55GB then53GB by03:24; newbulk stays held.

2026-11-08 03:38 PST: E5 memory bypass confirmed for inherited gunit new/base all-type bind verifies: parents921630/945734 live in plain session-373696/373777 cgroups, outside ot-heavy. S81 reports~24GB each plus23–34GB svc_rs Verilator children. Healthy, not stopped; root/S81 informed and future continuations must use existing ot-run requirement. E5 MemAvailable44GB/admission−37GB at03:34, so this is material outside pressure.

E6 automatic03:33 cleanup tick is running normally (PID3946260); scratch remained53GB at03:36. No manual cleanup/restart. New bulk remains held. HBM QOUT qualification requested a~1GB rehome from queued E4; advised I2 scratch244GB, with truthful current memory admission23GB at03:34 (fresh charge258.8GB), so stage complete input and re-check before owner cancellation, not claim immediate admission.

HEAD CTL no-dir issue is intentional spill-copy protection, not an alias failure: marked copy on I2 stays ineligible to a new continuation while original spill client and separate proof are live. Owner preserves marker/proof, waits normal copyback, then resumes canonically on E4 with corrected guide. Fleet bypassed nothing.

## E5 actual infrastructure kills — 2026-11-08 03:39 PST

Earlyoom journal confirms SIGTERM at03:34:14 to Verilator1495101 (svc_rs t4,25,869MiB RSS),03:34:27 to1499743 (t5,24,017MiB),03:34:53 to1503080 (t6,33,531MiB), at3% memory threshold. These are inherited unadmitted gunit full-plan verify children under plain SSH-session parents, not RTL/geometry regressions and not kernel MEMCG kills. Root and S81 owner informed to classify the affected rows as infrastructure-stopped and avoid a fresh broad sweep. Parents may continue; no process or guard touched by fleet.

2026-11-08 03:44 PST: Expanded E5 incident is31earlyoom SIGTERMs between03:31:02–03:34:53:30Verilator lint children plus1productionYosys. Compact exact list at handoff/fleet_earlyoom_20261108_0331.tsv (also E5 own diagnostics/earlyoom_20261108_0331.tsv). Yosys3905218/RSS21,992MiB maps to svc_lo_dsdv_svc_rs_w__t1 a9, E5scope3902186-1794079360/waveunitkw-s81-svclodsdvsvcrswt1-9-59306; journal exit-handler PWD proves identity. AP recorded INFRA/do-yosys Error241 at03:37:36. Old flat form remains held; no same-form relaunch. Root/S81/SVC notified; resource failure must not become RTL/geometry regression.

Other new terminal rows forwarded to owning leads without relaunch: QC sle_su_c0418be8bcee1 flow-error; QC sle_fw_v3 e4c8e9719aae admission-tools transfer failure beforepayload (wave+QC); QC sle_hc1 cl7d3605083558fa55d4fe DPL0033; S81leaf t36 0d8b07e2bb49 GRT0116.

## Later diagnoses — 2026-11-08 04:07 PST

QC sle_su_c0418be8bcee1 failed CTS on a correct initial tap-capacity guard, not E5earlyoom: E2scope2171889-1794137038, preflightPASS/LECexit0,37930registers/32taps, then initialtapcapacityinvalid. QC owner measured real clk_t8=5540sinks versuscap1200; redistribution moved3540 but no capacity within200um. Owner develops a finer structural grid, no cap/radius waiver or skip.

HBM q_mca7d5a0f529c66 final NOTSIGNED: TT+246.26ps, FF−48.71ps/31non-port endpoints,3slew, DRC0/ant0/LECexit0. HBM child has measured cause u_rrl558→559 from clk_t20early−160ps to clk_t7late0; images viewed, noECO. It develops co-root reset components where span permits, otherwise a phase-safe form; no relaxation/retry.

HBM QOUT original E4 qualification had already admitted before rehome was considered, and failed beforeLEC on bare --lec-mem 48 meaning48 Docker bytes. Owner preserves that failed log and runs exactly one corrected I2 re-sign with --lec-mem 48g/newoutqout_resign_fa_i2/controller1373314; no old payload active or duplicated.

KV RF-vC pilot wait was notFIFO: noncritical4T/16GB request subject to I1loadcap168 whileload171, despite later memoryheadroom; E4pickonly6GB so not eligible. Owner’s exact cancel raced I1admission after653s; tool explicitly left payload running in scope1966433-1794138168. Owner detected before any I2successor, preserved healthy synthesis, and collects native logs. I2capsule3.6MB remains unrun. No fleet signal.

SVC I2checkpoint scope1007704-1794137643 admitted after309s but failed beforeC++work because effectiveO0 invalidated O1PCH and ordinary .fast/.slow fallback headers were absent. No newOOM. Owner preserves failure, adds forwarding headers to unchanged base PCH, and resumes same96GiB/J1/O0make checkpoint; noRTLchange/Verilation.


## Fleet continuation — 2026-11-08 04:14 PST

Canonical fleet status: E2 admits 30 GB / scratch 135 GB; I1 admits 85 GB / load 138 of 112 / scratch 272 GB; I2 admits 117 GB / load 110 of 112 / scratch 228 GB; E4 admits 72 GB / load 79 of 256 / scratch 657 GB; E5 admits 1 GB / scratch 208 GB; E6 admits 401 GB / scratch 52 GB. These are volatile admission observations. E6 new bulk remains held against its unchanged 50 GB floor; no deletion or cleanup restart requested.

t35's quiet GRT log does not imply a hung build: container dpkit-ot_s81sl_leaf__t35-3748393 has OpenROAD PID 3949901 at 122% CPU, CPU time 1:49:49 versus elapsed 1:29:35. Parent and S81 lead informed. All six migrated AP rows still RUNNING, with no new terminal receipt in canonical state.

Newly collected HBM vsN1 job 14272b3be9f9 is DONE-STRUCTURAL: final TT +23.45 ps, FF -155.56 ps on 2523 endpoints, TT 461 / FF 446 slew violations, DRC 0, antenna 0, NOT SIGNED. An earlier review sentence refers to different hold numbers; final signoff fields are the current evidence. HBM owner notified to cover the structural diagnosis; no late ECO or retry.

KV Eo owner reports all I2 saved-DB timing diagnostic runs terminal with exit 0, while route remains held; exit 0 is not a SIGNED claim. Its E6 retained inputs/screens are inactive and receive no further staging. I1 PC43 full LEC scope 1859707-1794137953 remains healthy at about 29 minutes / one busy CPU / 1.6 GB; leave it running.


2026-11-08 04:18 PST: HBM QOUT corrected official current-fa re-sign completed on I2 at /srv/opentallas-scratch2/claude/codex-hbm-open-0222/qout_resign_fa_i2. Owner reports PROVENANCE SIGNED / LOCAL_PASS_NEEDS_PARENT; LEC 42882/42882 EQUIVALENT, zero diff/undecided; TT +144.62 ps, FF 4991 port / zero non-port violations, DRV 0/0, DRC 0, face 10888 PASS. HBM/root have READY-COUNT. The previous bare --lec-mem 48 byte-unit infrastructure failure is closed by the corrected 48g qualification, not relabeled as OOM or RTL. Preserve capsule and completed unit.

E5 inherited broad verify parents 921630/945734 are now absent; sudo earlyoom journal has no new kill since 04:00 PST, with 17.85% memory available at 04:13. Existing jobs untouched. All six migrated scopes remain active; fresh t24/QCstm GRT logs at 04:16, no terminal receipt.


## Claude handback — 2026-11-08 12:22 UTC

Fleet has stopped new transfers/launches; healthy jobs remain untouched. No fleet-owned transfer, compiler, or pending admission client remains. No deletion, cleanup restart, guard change, source mutation, or new frontend was made by this lane.

Six existing frontends migrated to complete I2 S2 kits by supported copy/link, preserving E5 originals, are still active at last observation: t35 a4 scope 3746226-1794134103; t11 a15 3851534-1794134365; station t24 cl64811a5d a14 3964651-1794134638; QC stm2 a7 4050584-1794134838; QC sta2 a10 54113-1794135315; QC sta1 a9 201558-1794135687. Prefix each with oth-ubuntu-. All use /srv/opentallas-scratch2/claude/codex-fleet-0222/staged/<tag>/gen; original frontends are sole producers, complete-copy receipts and .keep refs remain. Last stage: first four GRT, final two CTS. t35's quiet log is healthy: OpenROAD 122% CPU / 1:49:49 CPU at 1:29:35 elapsed; do not call stale E5 logs hung. All AP rows RUNNING; no terminal receipt collected.

Four station pre-CAD roots (t22, t14, t29cl, t44) were resited by wave, not fleet: I1 S3 to S2 with atomic exchange and preserved *.pre-resite-0222. Manifest I1 /srv/opentallas-scratch2/claude/codex-wave-0222/station_resite_manifest.json. Do not repeat. Station t18/t52 later healthy I1 GP per station owner.

SVC E6 scope 3156689-1794134077 was an actual 64 GiB kernel MEMCG OOM (cc1plus RSS about 63.5 GiB), not an inference from exit 143. Its intact checkpoint was copied without deletion to I1 and I2 /srv/opentallas-scratch2/claude/codex-svc-rtl-0222/miter_resume. Exact kernel excerpt is miter_resume/infra_memory/epyc6_3156689_memcg_20261108_030600.log. I1 unadmitted client was owner-canceled; I2 first resume scope 1007704-1794137643 failed before C++ work because O0 invalidated O1 PCH and ordinary fallback headers were absent. SVC owner is adding forwarding headers and owns any corrected 96 GiB/J1/O0 resume; no pending fleet copy/client. Do not duplicate that compile.

E5 earlier 31 earlyoom SIGTERMs (30 inherited broad-verify Verilators plus production Yosys) are recorded in handoff/fleet_earlyoom_20261108_0331.tsv, also E5 own diagnostics path. Production victim was S81 svc_lo_dsdv_svc_rs_w__t1 a9 / scope 3902186-1794079360; AP Error241 is infrastructure, not RTL. Broad verify parents 921630/945734 are now absent; no new earlyoom kill since 04:00 PST at last journal read. Owners have exact classifications.

E6 remains at canonical 52 GB scratch free (direct df rounds 53), root 120 GB, unchanged 50 GB scratch floor. New bulk remains held. Existing ot-autoclean.timer next tick is 12:31:20 UTC / 04:31 PST; no manual action. Previous 11:33 tick completed 11:37:33 UTC exit 0, protected/count hits 0, reaper removed 0. Preserve KV e1_ds + kit_e1 live provenance references, finished readlease objects and all fresh screens. KV Eo diagnostics are terminal, route held, retained E6 inputs inactive. PC43 full LEC I1 scope 1859707-1794137953 was healthy; preserve.

RCK live alternates store I1 /srv/opentallas-scratch2/claude/s81-rck-10/repo/.git/objects is registered with current own worktree in ~/.local/state/wt-reaper/protect.d/codex-fleet-0222-rck-alternates.txt. Preserve until owner retires dependency.

Closed follow-up: HBM QOUT corrected official re-sign at I2 codex-hbm-open-0222/qout_resign_fa_i2 is SIGNED / LOCAL_PASS_NEEDS_PARENT, LEC 42882/42882 equivalent, TT +144.62 ps, FF 4991 port / 0 non-port, DRV 0/0, DRC 0; HBM/root have READY-COUNT. Its old bare --lec-mem 48 byte-unit launch failure is closed. QC RF-vC cancel raced admission; healthy I1 scope 1966433-1794138168 remains alive, I2 tiny capsule is UNRUN, no duplicate. All newly observed AP failures were forwarded to die owners; latest KV leaf t3 ac9f0372acba LEC inequivalence and HBM vsN1 14272b3be9f9 large hold failure are structural, no fleet retries.

No outstanding OWNER question added by fleet. Parent should consolidate dirty shared coord reports plus the earlyoom TSV; no git retry loop or other agent work was changed.

Handback addendum received directly from SVC owner: corrected I2 checkpoint scope oth-ubuntu-1793538-1794139284 completed exit 0, base H8_ENGINE PASS errs 0, three controls caught 576/288/576. No new OOM; O0 forwarding-header fallback succeeded preserving generated model and completed objects. Results: I2 /srv/opentallas-scratch2/claude/codex-svc-rtl-0222/miter_resume/launch_o0_header.log. No further copy or compiler pending.
