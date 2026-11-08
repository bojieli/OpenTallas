# S81 station takeover 2026-11-08 02:22 PST

## Current step
CODEX took over t45 ring-tap class fix deployment on codex/s81-station-0222.
No prior KW-FIX-34-T45 child job found. Wave t45 remains a11.

## CODEX notes
- Cause already established: ring_taps used stale explicit tap indexes while actual reset relays use generated grid. The fixed export is branch857e197e14c, read from epyc2 s81-station-1/rt/tools/die_plan.
- Private prototype now epyc2 /srv/opentallas-scratch2/claude/codex-s81-station-0222/prototype. Exact three connection changes derived by fixed canonical ring_taps: dn_s_2N_L0x5_i reset11 -> reset3 (160.57um); ft1_i reset2 -> reset4 (238.76um); ft2_i reset2 -> reset4 (300.01um). Collector tree already uses reset3/reset4. Equal-depth reset, PIN CYCLES0. reset_tree JSON bound RTL hash updated; tree/Tcl unchanged.
- Prototype does NOT claim a new strict die bind receipt. Metadata says PENDING independent canonical rebind.
- Independent cached-asbuilt strict rebind queued on epyc2 via ot-run48GB1T: /srv/opentallas-scratch2/claude/codex-s81-station-0222/rebind, log intel2 /home/ubuntu/codex-s81-station-0222/rebind.otrun.log. Uses full unchanged wave plan and exact source28 manifest;3.2GB cached graph avoids repeatedELAB.
- Private overlay created (all other files reference unchanged canonical bind); kit-rtl dry launched, topology dry follows.
- Initial I1 source fetch could not resolve intel2 alias then hub fetch timedout; no source work lost. E2 own recent station clone used instead. No shared source edited.

## Next
Collect kitRTL/topology dry, current strict re-emission; compare canonical t45 generated files to prototype.
Render/view the corrected reset rings before ONE pilot through PLACE; coordinate shared config solely through wave owner.
Collect station DRV batch t22a11/t29cla12/t44a6/t14a11; no duplicates.

## 02:45 progress
- KIT-RTL prototype dry_rtl2 PASS:6sources, unbound0,2spareout/2narrow baseline.
- Default topology dry FAIL KIT_TOPOLOGY_BIND_STALE. Existing globalnative receipt differs because unrelatedLPtap edits; no waiver or stamp.
- With separatelyproved faa6c88d4a selected-reset-scope helper (defaultOFF) and OT_NATIVE_RESET_SCOPE=selected: actual t45 prepare-stations PASS rc0, problems[], native/rawstages0. New private dry_rtl_selected only.
- Actual reset grid plan rendered/viewed: local /tmp/codex-s81-station-0222/results/geom_review/t45_ringtap.png; own E2 t45_ringtap.png. PASS-COND onePLACE only, route held.
- Cached strict bind initially queued E2; own unstartedclient3763649 canceled. Portable5GB capsule stagedtofleetintel2, unit3940459-1794134573. Attempt1 FAIL missingtoolsroot die_port_bind module beforemapping; immutablebind.log kept. Added53MBexact rootPython helperfiles, attempt2 relaunched; no P&R performed.
- Real stationDRVbatchfailure diagnosed: all4 waitingbeforeCAD on intel1scratch3rootfloor150GB (t22 log01:17:52, t14 log02:20:19). Wave safelyresited samepaths ontoI1scratch2 preservingfrontends and8KBold dirs. No stop/retry/config edits; originalpoll shouldprogress.

- 02:49 actual station progression afterresite: t44a6KIT_RTL exit0 thenKIT_TOPOLOGY_BIND_STALE FAIL (noCAD), t29cla12KIT_RTL admitted. Same globalnative-reset staleness class diagnosed by S81types, no blindretry. Current strictfullbindattempt2 healthyfleetintel2 unit4050060-1794134836/PID4050173,100%CPU,16GBRSSat1m51. Its output may replace the stale canonical generation context once complete. Logs/evidence preserved.

- 02:55 selected-scopeactualcohort check PASS: t22,t29cl,t44,t14,t45 allmatchoriginalproducer/currentselectedcontext. ActualchangedLPcontrol dsdv_slice_lepe_mu_LP__t2 rejected(false). Evidence E2ownstation_scope.json/rc0, no stamps. t29cl/t14join t44withdefaulttopologyFAIL afterKITRTL0; oneclassbatchafterC1PLACEpilot.
- Private fallback prepared E2own/fallback/plan_private_t22_t44.json + FORM.json: adds onlyt22/t44 to globalreset.relay_lockup.types/taps, using existing4bec6ebc2a4 generatorfix. NoPORchange, no launch, PIN CYCLES0; intendedonlyif targetDRVrepairleavesoneinternalrelay-removalendpointeach. Otheralreadyclosedstationst29/t47excluded.
- Portablebindmanifestnote: currenthealthyattempt uses relocatedbase/mapfile manifest /capsule/asbuilt_manifest.json with differentbytesSHA, so outputnative_receiptvalidonlyfor privatecapsulemanifest; never dropitintoPORsubject/stamp. Future portablejobs canusealreadycopiedoriginalbyte-identicalmanifestinside /capsule/src/physical/die_plan/s81/bind/asbuilt_b178_coll_h2_2249.json (relativebase resolvescorrectly). Currentresultusefulforexactt45reemission/privatecanary.
