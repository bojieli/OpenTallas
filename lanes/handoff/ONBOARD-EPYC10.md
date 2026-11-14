# ONBOARD-EPYC10 handoff (2026-11-13 18:31 PST)
State: DONE. epyc10 (Cherry 1062383 civil-redfish, 185.8.107.162) is a live full type-level build host in ot-run and the kit wave. Details are in the RESULT line of 2026-11-13 18:31 in lanes/COORD-REVIEW-QUEUE.md.
- ot-run: epyc10 admits 963 GB (avail 995, reserve 0, fresh 0, peak 0) load 0/96 run 0 root 4% scratch 6688 GB
next 16-thread 32 GB job -> epyc10
- Smoke PASS: intel2:/srv/opentallas-scratch2/claude/onboard-epyc10/smoke/ap (spec.json, unit.log, result.json); kit on epyc10 under /srv/opentallas-scratch2/claude/onboard-epyc10/smoke. All of it is mine and can be deleted.
- Backups: localhost ~/.ssh/config.bak-onboard10-*; epyc10 ~/.ssh/config.bak-onboard10, /etc/ot-heavy.conf.bak-onboard10; intel2 ~/.local/lib/fleet/{rehost1-kw38-spill-99d7dfcd,kw43-rootreal,isolate-1-kw46m-590d7d62e7}/ot-run.bak-onboard10-*, ~/.local/bin/{ot-reserve,ot-sizes-sync}.bak-onboard10-*, kw44-seal-ap/sealed-{ap,wave}.json.bak-onboard10-*; fleet hosts ~/.ssh/*.bak-mesh-1113.
- Open: (1) ROOT-MERGE: add epyc10 to the repo copy of tools/fleet/ot-run (HOSTS, HOST_ROLE, floors, SPILL, NO_AVX512), as still pending for epyc9. (2) HBM is parked, so epyc10 is not in dies.hbm lists and has no HBM src tree. If HBM restarts, copy kw45/src_hbm_main_d6b0b70323 from epyc9 first. (3) New die src trees from a wave switch (after the 11-15 04:00 freeze) must also be staged on epyc10, the same as on every other gen host.
- No ot-autoclean timer was installed. No Cherry API writes. AGIdock untouched.
