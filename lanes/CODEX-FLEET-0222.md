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
