# CODEX QC SC / RED diagnostics

COORDQ12 2026-11-01 18:50 approved the diagnostics/source events; older18:36 PREP permission holds are superseded. Source, absolute clock frame, real-view timing and parent adoption gates remain.

## Current steps
- SC: exact db9 current-factory051 kit / correctedsource98bbb copiedprivately. PersonallyVIEWED 572bitpin plan; centerstructured2389BUF24seed and339051projectedcells. Freshordinary SYNTH→PLACE only via ot-run16GB2Tdisk10 --crit, hostsIntel1/epyc2; frontendIntel2 PID3892686. Outputs hosts:/srv/opentallas-scratch2/claude/codex-qc-sc-red-1101/sc_place/qfd_dv_s5_sc2_leaf_pin1centerwideNcurrent/{run_place.log,run/.../3_place.odb}. No current duplicateproducer; d90SCbandpilot preserved. No CTS/STA/GRT/route follower.
- RED: actualoldPLACE+cap16assignment copiedprivately. PersonallyVIEWED actualnative CLKpin overlay. One import/rebind-only diagnostic,8GB1Tdisk2 --crit, hostsIntel1/epyc2; frontendIntel2 PID3999800. Runtime .../codex-qc-sc-red-1101/red_rebind/{rebind.log,rebind.rc,rebind_summary.json,red_rebound.odb}. Exactly34225nativeDFF CLK assignments to3452existing leaves; every selectedleaf8noninvertingBUFx8stages fromsameck. Full oldcell/otherITerm/BTerm/net guards. No PLACE/CTS/STA/GRT. Parent250/202.5frame NOTqualified by conditional296.37/231.92model.

Branch codex/qc-sc-red-1101@343baa122 (inherits experimental98bbb; doNOTmergewholeasproduction). Results/producer/reviews committed under results/qc_sc_red_diagnostics_1101 and results/geom_review/qc_sc_red_takeover_1101. SCexplicit sourceevent separates7baseleaf types/10replicas from2chain-end types; declared−387vsactualmapped42665FF neverconflated; immutable1364730 notchanged.

## Next
Collect actual admissions/results. SC3_place→actualLOOK/count/source-correlated sinkgeometry beforeCTS. REDactualrebind→compare nativecensus/rootframe, no STAcredit. Both jobs normalmemoryreservations; no timing/physical PASS claimed whilequeued. OWNER? none.

ROOT classification correction: RED296.37/231.92 versus250/202.5 is design-target deviation only, not a hardFAIL or mandatoryredesign. ActualrelatedpairTT/FF+countalignedcontract decide. No extraabsolute-latencygate added; importscope remainsunchanged, parent/currentviewqualification stillopen.

ADMITTED: SC1787571-1793596546 epyc2 activefreshSYNTH. RED1765031-1793596386 epyc2 terminalexit1 atfirstCLKdisconnect ofdont_touchmp_ck_T000120_out; nooutputODB. DiagnosedAPIprotection/sourceeventnotphysicaltimingfailure. Newownr2dirtemporarilyunlocks onlyexactDFF+old/newleafnets withtry/finallyrestoreandDNTflagsguard; sameinput8GB1T, dispatcher110288, noSTA/CTS/GRT. Originalfailurepreserved.

RED actualPASS r2 epyc2unit1863605-1793596839 exit0:24516CLKrebindings/34225nativeDFF/3452leaves/8269fixednodes, maxactualreach15.7705um; alloldcell/master/pose/status/nonCLK/BTerm/net/DNTflags guardsPASS. PersonallyVIEWED actualnativebindingimage, old75umdiagonalclustersgone. ScopeIMPORT_REBIND only, noCTS/STA/GRT/timing/parentcredit. SCfreshSYNTH continues.

Approved continuations now queued via normalot-run16GB2T onIntel1/epyc2: REDfixedCTS dispatcher1273625 (/red_cts_fixed), SC TAP-aware GPL→resize→DPL dispatcher1273626 (/sc_place_tapfix). Both0725pinnednormalbundle; RED11fileguardPASS. Sourceplan/slice/TCL112sitegeometrycorrectionrecorda96799d07; newprivateREDtemporarilyFIRMsoriginalPLACEDcells/restoresstatuses+DNT, withstrictunchangedpose/graphguards. NoSDC/gate/sourcecyclechange; nativefailuresallpreserved.
