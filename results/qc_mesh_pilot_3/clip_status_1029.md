# Inherited pilot clip collection, 2026-10-29 01:20 PDT

All 18 inherited clips accounted for; existing live jobs remain untouched. No new pilot variant. A2 full MC/DRC packet is in a2_drt (physical FAIL retained).

| Trial | mid | core | c0 | c1 | c2 | c3 |
|---|---|---|---|---|---|---|
| A2 | EXIT0 | EXIT0 | EXIT0 | EXIT0 | original137, 40GB c2r EXIT0 | EXIT0 |
| B | EXIT0 | EXIT0 | EXIT0 | EXIT0 | original137, owned40GB retry137 | EXIT0 |
| A3 | EXIT0 | EXIT0 | EXIT0 | running, 27th guide iteration | original137, owned40GB retry running, 3rd guide iteration | running, 14 violations |

Original roots: epyc2:/srv/opentallas-scratch2/claude/qc-mesh-pilot-2/{a2,b}; intel1:.../qc-mesh-pilot-2/a3. Owned retry roots same hosts .../codex-qc-mesh-1029/{b,a3}/c2retry. Existing A2c2r remains at original a2/c2r. A3c1diag is a separate capped3iteration diagnostic EXIT0, not a substitute fullclip.

B c1+c3 newly copied to OWN b dirs and both-edge TT/FF re-time EXIT0 (unit oth-ubuntu-322337-1793261872, intel2 client3697169/log codex_qcmesh3_b13_sta3.log). Each has two root/entry n_in M9 MinStep harness markers, no new design DRC. Two earlier wrapper-launch failures were corrected: absent ot-run PATH, then missing remote ready_b13.sh; no routing repeat.

B c2 owned retry FAILED after61st stubborn iteration at19 violations: run.log EXIT137. Kernel 2026-10-29 01:16:11 confirms Docker memcg40GB OOM, openroad PID1933903 anonRSS41,858,952kB. ot-run reports EXIT0 because inherited run.sh's trailing chown hides OpenROAD's status; run.log and kernel establish failure. Original24GB OOM is retained. No additional retry: project priority is actual connected fullclock+signals/parent realviews, and this stalled pilot has known structural M8 MinStep via/trace-end DRC. A2 completed35DRC (18design M8MinStep+17harness), A3 diagnostic confirms same design failure class. B cannot compose fullclip MC, and no pilot group is adopted.

Owner: mesh successor may redesign actual feeder/access geometry after primary fullclock integration; ROOT/QC retained explicit no-extra-variant instruction. Buffer7stage pilot full duty/variation safety remains unqualified; U61 alone is never die release.
