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

## 03:22 milestones and active work
- Canonical cached strict bind PASS: 398 partitions,205types,873crossings,606281crossingbits; errors0,unbound0,tied0,undriven0,multiply_bound0. Native receipt v2 covers205types. I2 capsule/bind, ot-run unit4050060-1794134836 exit0 with outputs copiedbacktoE2. This remains the PRIVATE relocated-manifest context; no POR receipt replacement or stamp.
- The t45 canonical .sv is BYTE-IDENTICAL to the three-edit prototype (directdiffempty). Own source branch codex/s81-station-t45-0222@b41f85e869b3fee33f83ea035e1fc44fd9473217 pushed to hub (361 plus857 ring-tap hunk). Five focused ring-reset tests PASS. Own pilot I2 /srv/opentallas-scratch2/claude/codex-s81-t45-0222/requests/a1/spec.json and run.log: KITRTL0,selected TOPOLOGY0,GENactive; only PLACE/GEOM, no canonical enqueue or route.
- T36 north3 physical profile committed and pushed on codex/s81-station-north3-0222@211afa986cd6d5a11403658e3a62d17ef0b04ab9. Exact profile dry PASS (five widened banks,0new FT-bay intersections). Actual prebuild overlay image viewed and review recorded. Separate I2 work root /srv/opentallas-scratch2/claude/codex-s81-north3-0222 avoids the full-bind spill marker on the station lane root. Current request a2: KITRTL0,TOPOLOGY0,GENactive. a1 failed GEN missing tracked catalog, no P&R; preserved.
- Correction to earlier catalog diagnosis: rom_declared_logic.json is TRACKED blobd0f2319; missing sparse coverage, not untracked evidence. Types lead expanded source361/tools/mem_compiler; canonical SHA e0cfba4b9fb5f9b4ad82092adc51d671f05e8660649e9f92f6e9adb3d0942a14 matches kw33. Own t45 source includes it.
- Five older failed stations t27/t36/t37/t43/t49 are stale FLAT W140/out_min140 forms omitted from the per-port wave (SSTN-HOLD-2 11-07 00:28). Actual t27/t37/t43/t49 config reads confirm; t49 FF worst launch clk_t60 source-140 versus captureclk0. Fresh current per-port form is a structural clock-contract rebuild, no ECO. All older failures retained. t37 initial synth151788std/0macro, so previous521k figure is not the initial count.
- Actual t27/t37/t43/t49 placement images viewed under /tmp/codex-s81-station-0222/*_final_placement.webp; t49 clock image viewed too. No macro walls; distributed FT rows and dense N/S pin rings plus long buffer bands in old FLAT repaired forms. Current per-port rebuild removes the large artificial window; actual new PLACE must be viewed. T36 additional north density fix proceeds in its one private pilot.
- T36 older spacing pilot failure confirmed MEMCG OOM on epyc6 at04:12:44UTC, killed PID1599778, anonRSS33474848kB; no route verdict. Existing actual2-row PLACE maxdensity0.76268,24bins>0.7 (23north), viewed. No unchanged retry; new three-row profile plus8.64um band depth is the structural correction. Naive4-row form held because it would newly intersect71 FT15-stage0 cells.

## 03:35 physical pilots and broader collection
Both pilots have passed generation lint and contract preflight, and normal PLACE is admitted on I2:
- t45: unit oth-ubuntu-981477-1794137582; request /srv/opentallas-scratch2/claude/codex-s81-t45-0222/requests/a1/continue_generated, kit /pilot/attempt_1/gen/slice_station__t45 under the same lane root.
- t36 north3: unit oth-ubuntu-990965-1794137610; request /srv/opentallas-scratch2/claude/codex-s81-north3-0222/requests/a2/continue_generated, kit /pilot/attempt_2/gen/slice_station__t36.
The manual request folders initially lacked the approved future_lec bundle, so both stopped after successful GEN before CAD. The exact approved 289149dea5b five-file bundle was copied read-only from the types lead and its metadata matched both specs. A private continuation reused those exact generated kits, with guards requiring the prior lec_tools FAIL, matching freeze type, and no physical ODB. Lint, preflight, LEC staging and PLACE remain normal. No GEN repeat or failed verdict overwrite.

The two additional station frontends t18 a14 and t52 a18 were also found stuck on I1's root floor. Wave safely resited their existing paths to scratch2 without stopping them. Both now completed KIT-RTL with exit 0 (units 1539299-1794137273 and 1620598-1794137436); collect the next topology stage.

Current-route collection found t24__cleece78ec a12 physically finished with TT setup passing, FF -11.80 ps (449 port-start,3 other), slew93/102 and LEC EQUIVALENT19023. Its review is queued; the slew count exceeds the near-miss rule, so no new ECO. Viewed actual final placement: one compact north ring strip beside distributed FT rows; no macros, but dense pin-ring/word-control region. Worst slew pins are CLAND ft0 selector B inputs (354 ps versus320). This joins the control-drive/face-density class for a structural form.

Correction: two t50 rows have older detached ECO chains still active, so their raw route signoffs are not terminal. Leave healthy existing chains untouched. Latest cl394 i2: TT+149.82, FF-1.46 (5 port+1 other), DRV0. Latest cld84 i1: TT+148.08, FF-9.28 (70 port+31 other), DRV0. Their final placement images were viewed; both have north/south ring strips and distributed FT rows without macro walls. Collect terminal results; do not launch another ECO.

## 03:48 collection and corrected t24 diagnosis
- Both t45 and t36 north3 pilots are healthy in normal global placement (3_3_place_gp); no route is released.
- t27/t37/t43/t49 generated-only preparations have KITRTL 0 and selected topology 0, GEN active. Their helper stops before PLACE and records physical NOT RUN.
- t24__cleece78ec a12 is terminal NOT SIGNED; autopilot review d578afa6cd07 confirms no ECO because 452 hold endpoints exceed100. Actual final-Verilog pin mapping corrected the earlier slew classification: 93 TT/102 FF violating pins correspond to only THREE nets, ft0/net35904 (BUF10), ft0/net35923 (BUF6f), ft1/net35625 (BUF10), all local landing-ring control. No missing pin maps. Holds449 input-port +3 other; actual worst other is reg-to-output ft2_o[491], -11.80ps, not an internal reset miss (worst shown reset-removal +2.63ps). Keep no-ECO; same ring control drive/face class as t14/t22. Private generated-only current-source slew50/cap20 preparation launched at I2 /srv/opentallas-scratch2/claude/codex-s81-station-prepare-0222/slice_station__t24__cleece78ec/request, frontend1403709. No canonical config change or physical release.
- Both inherited t50 detached repair chains confirmed truly LIVE on E2: cl394 i3 DRT, cld84 i2 DRT. Prior signoffs unchanged (cl394 i2 FF-1.46,5port+1other,DRV0; cld84 i1 FF-9.28,70port+31other,DRV0). No stop or extra ECO.
