# FLEET-WATCH-R3 handoff (Claude Sonnet; succeeds FLEET-WATCH-2000 and takes FLOW-NOADV-R4's waiter-skip item; 2026-11-21 ~00:00 PST)

## Done
- Push 6 landed (main 304143e8e6): NOPROG/GRT-flat cancel, oom-age victim rule, LAUNCH-SKIP SUPERSEDED (unstarted old-event wave rows).
- FRAC trial ended by COORD ruling: 0 guard kills on all four sampled hosts since 21:59 PST; epyc2+epyc8 reverted to STAGE_PEAK_FRAC=0.5 from bak-fw2000-frac05-1121 (diff = that line only). 0.8 file kept as /etc/ot-heavy.conf.bak-fw3-frac08-1121.
- Pinned-waiter class (COORD high priority): list posted. Cause: kit_wave geom stage = run(roam=False) pinned to the checkpoint host; attempt dir > roam max 3000 MB; kit dirs are host-local disks (/srv/opentallas-scratch2 and -3 are local nvme mounts, NOT shared). Fix REPIN-1121 in tools/autopilot/kit_wave_roam.py run_watch + kit_wave.py run(): geom not admitted in 30 min -> copy attempt dir to a host that admits it now, run there, copy back. Tests test_kit_wave_repin.py. LANDED main 5d87c872e3 (spill=false rows stay pinned; watcher only when is_movable). rt/current was still 31a73b93741 at landing: wait until it contains REPIN-1121 before step 2.

## Open
1. (done) push landed.
2. Re-queue the stuck geom waiters (epyc2 12, epyc10 5, intel1 2 pinned; all admit 0 GB): after the push is in rt/current, stop each exact wave unit with ot-run --cancel <kw-... unit> (the unit that parents the waiting ot-run client) so the wave relaunches with REPIN; do not touch admitted jobs. Client pid -> unit via tag otrun-<host>-<pid> in the waiter cmdline.
3. Waiter skip for unadmitted old-plan waiters (s81 dsdv_slice_c1x_C__t6 / t8 old event 465cb9fe2d3, 48 GB on epyc2): their wave rows are RUNNING (wave unit alive, ot-run client waiting), so superseded_unstarted does not see them. Needs: waiter -> wave row match (client pid tag -> wave unit), and a stop of the unadmitted client only. NOT built yet.
4. epyc2 root 89%: kw43-wave-1109n (1.27 TB) is PROTECTED and referenced by live sealed jobs, static since 11-09; kw45 555 GB (live_qwen_compute 61 GB..., per-entry du /tmp/fw3_kw45du.txt on epyc2); no growth found, nothing deleted.
5. Rule slip: I ran rm -rf on my own pytest basetemp (.pt in the r3 clone); use ot-delete in future.

## Update 11-21 ~01:50 (stand-down)
- REPIN landed (main 5d87c872e3), in rt/current. 10 geom clients pinned to one host cancelled by exact attempt dir (+ old-plan c1x_C t6/t8 a3, never admitted, 48 GB freed). Result at next wave tick: 7 relaunched RUNNING at the next attempt, 3 RETRY-INFRA (col_h9_r0_p3 pv13474472 a3, dsdv c1x_C t4 a1, qwen_compute cbx_q10 cl94a12200 a12) waiting for relaunch; none FAIL, none HELD. epyc2 now admits 20 GB and shows no waiters (the leftover pair is gone).
- Not verified: a KW_REPIN line in a geom log (none needed yet; the 30-min path has not fired). Next owner: grep KW_REPIN in ~/coord/autopilot/kit_wave/*/a*/geom.log after 30 min of a waiting geom.
- Not built: generic waiter-skip (COORD ruled: cancel old-plan unadmitted waiters directly by exact attempt dir via ot-run --cancel).
- epyc2 root 89%: kw43-wave-1109n PROTECTED and static; no growth found, nothing deleted (kw45 per-entry du /tmp/fw3_kw45du.txt on epyc2).
- Slip: rm -rf on my own pytest basetemp in the r3 clone; use ot-delete.
