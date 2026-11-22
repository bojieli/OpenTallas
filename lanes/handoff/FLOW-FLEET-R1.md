# FLOW-FLEET-R1 handoff (Opus 5.5, lane for COORD; source lanes/FABLE-FLOW-2200.md)

Lane clone: epyc9 /srv/opentallas-scratch2/claude/FLOW-FLEET-R1/repo (cone tools,bin,tests). Scratch tmp: .../FLOW-FLEET-R1/tmp.

## Item 1 epyc7 thread cap: DONE 11-21 21:5x PST
- epyc7 /etc/ot-heavy.conf: THREAD_CAP_FACTOR 1.0 -> 0 (value of .bak-fleet7r1b-1122); LOAD_CAP_FACTOR=1.2 kept with
  `#@cap LOAD_CAP_FACTOR owner=FLOW-FLEET-R1 expires=2026-11-23T06:00Z` line. Pre-change copy: /etc/ot-heavy.conf.bak-flowfleetr1-1122.
- Admits resumed: last epyc7 not-admitted REQUEUE 21:55:10 (waiter from before the change); 7 waiters -> 0, run 26 -> 29.
- Convention + check: main 3eb6e99f80 tools/fleet/host_caps.py (+test). intel2 fleet-ops-r/host_report.sh appends HOST-CAPS line
  (backup host_report.sh.bak-flowfleetr1-1122).
- TODO 2026-11-23 06:00Z: LOAD_CAP 1.2 expires -> decide revert to 0 or renew.

## Item 2 GRT-STUCK watchdog action: PUSHED main 403477dcd9
- noprog_watchdog.py: GRT-STUCK BAD verdict (>=3 rounds flat/rising, >6 h in GRT); spared: wave attempts (grt_flat_pass), re-sign/ECO,
  PROTECTED-DBS, lane post in last 2 h. Hub writes policy/protected.tsv + posts_recent.tsv. Takes effect when rt/current follows.
- At push time, 4 of 19 GRT-0273 rows qualify (sle_ctl padW5 epyc10, hd_lep0N-3749933 epyc7, t73 epyc7, kv3_hgi_v1 intel2). The others
  are still falling >2 % per round window. TODO: verify first REPORTED/CANCELLED in NOPROG-TABLE.

## Item 3 tree copies + COORD add-on (.fork.json rejected by src_manifest): IN PROGRESS
## Item 4 count drift: TODO
