# FLEET-WATCH-R7 handoff to FLEET-WATCH-R8 (2026-11-21 ~13:2x PST)

Job: keep 7 gen hosts (intel1 intel2 epyc2 epyc7 epyc8 epyc9 epyc10) healthy. Never touch epyc4/known_hosts. Rails stay (admission, floors, delete guard, OOM).
Rules: ot-delete only (guard decides), kill exact PIDs after cmdline check, bg waiters, post via bin/post.sh, COORD only on emergency/decision/stand-down.

## State now (free GB scratch2): intel1 ~186, intel2 ~1230, epyc2 ~128, epyc7 ~304, epyc8 ~145, epyc9 ~205, epyc10 ~115 (DRAINING). localhost root ~205 (reserve 100).
## Live items
1. epyc10 DRAINED via kit_wave.json host_drain {epyc10: 9999} (commit f987340fb1). UNDRAIN when scratch2 > 200 GB:
   cd /srv/opentallas-scratch2/claude/rt/current/tools/autopilot (on intel2); python3 -I kit_wave_edit.py -m "FLEET-WATCH-R8: UNDRAIN epyc10 ..." --unset /host_drain/epyc10 ; rm ~/.cache/ot-run/drain_caps.json. Post both transitions.
   Same mechanism drains any host (set host_drain {host: 9999}); trigger rule: free <120 GB or fall >80 GB/h. ot-run caches caps 10 min.
2. Restore poll: localhost detached script scratchpad/w10.sh (log w10.log, pid 3068251 at 13:2x) re-adds epyc9/intel1 to gen_hosts at >=250 GiB with >=2 h to floor. Check alive every 30 min; restart detached if dead.
3. Owner asked: unsigned/failed/superseded attempt dirs deleted; only SIGNED need export; signed-not-in-store wait for FLOW-CANARY-R2 ingest fix. My batch (epyc10/8/7/2, 300 dirs each, idle >=2 h attempt_* under kw43-wave-1109n/1109): guard SKIPPED ~97%: "protected (kit_wave.json src/bind of record/marker/prov)". Deleted 7/3/3/0. So wave attempt dirs are all guard-protected; that is a delete-guard breadth question for FLOW-OPS (not overridden by me). Script: scratchpad/batch.sh.
4. Guarded ot-auto-retire pass (timer + `ot-auto-retire-run.sh apply`) freed in 4 h: intel1 52, epyc2 14, epyc7 48, epyc8 34, epyc9 78, epyc10 26 GB. Nothing more deletable now; epyc10/8 rely on owners exporting signed trees (list in hub post 66e27cfbfc).
## Known causes this shift
- git pack leak (deleted-open packs, orphaned git log -S): fixed gc.auto=0; timeout 600 rule.
- epyc7 docker create stall = writeback stall on shared nvme (umount in create blocks); cleared when Dirty drained. Check: time `docker run --rm --network=none --entrypoint /bin/true opentallas/orfs:asap7lock-grtT3` (<10 s ok). Do not restart dockerd with heavy containers.
- epyc10/8 falls of 100-170 GB/h were bursts (staging + route writes), no single file >1 GB, no runaway.
- fable-pd-head-clk deletion = ot-auto-retire epyc2 11-18 03:56 (post 4524dcc726); guard gap noted.
- disk_rate.py pushed (470792e6e4): alerts carry lsof +L1 holders, one alert per state.
- localhost deletes done with manifests (scratchpad/otd copy of ot-delete + OT_DELETE_MANIFEST_DIR=~/.local/state/delete-manifests); do NOT touch pcv3repo/fleet-viz server, ~/wt/qc-types-r-1116, wt-admit, ghpush, ~/afg, trainforensics, closed_archive, signed-export-1114.
- Gen-host lines: keep no staging on localhost; send private kits to epyc7/8/10/2 (epyc7 ok again).
## Every 30 min
disk+load+dirty+lsof +L1+D-state per host and localhost, exporter log (~/bin/ot-auto-export/rtx.log), ot-run --status waiters/idle, 2-h hung scan (age>2h, CPU<1%, e.g. orphan yosys ppid 1), capped hosts used by lanes. Hub post every ~2 h.
