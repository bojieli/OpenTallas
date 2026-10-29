# PARKED on explicit Claude reset 2026-10-29 14:02 PDT

No engineering/launch after reset. Branch codex/qc-a0-1355 based exact452603b6fbb; ownWT intel2 /srv/opentallas-scratch2/claude/wt/codex-qc-a0-1355. Runroot intel2 /srv/opentallas-scratch2/claude/codex-qc-a0-1355. No own liveheavyjobs (only4staticgenerator invocations completed). No sourceRTL/pins/period/uncertainty/latencycycle/interface change. NoCTS/P&R/STA launched. Sharedcore_infra opt-in452603b6fbb alreadymain remainsOFFforproductionA0 perCOORD.

InheritedcurrentA0 state: selectedRRST graph-home places areGEOMPASS-COND NLrr2/NKrr1, r2r0>405, pin15um, gateenable<=396; actualoperationalcontractproofgapsclosed byDIE-QC34/35. DoNOTredo0830failedplacements. NativeTritonCTS failed earlier; latestplannedtreecopies dqc36-a0/cts fail NLFF−654.46/5718, NK−1105.87/7766 with singlemp_a0_t7 drivingallregisterICGs+rootp8branches. AllA0CTSjobs terminal, peer dqc36-bb1 untouched.

WIP changes results/qc_die36_1029/a0/gen_a0_tree.py ONLY: defaultT11/nonspread path unchanged; opt-in --spread --stages N. Movesclockfeedfromsingletrunknode into sharedspatial4-way tree; macrosawareplannedbufferhomes projectoutsidehardcorehalos, noRTLgate motion. Native oldcensus and signedmacroLiberty unchanged. No additional core_infra sharedtool change.

Staticcontrols retained:
- T11 NL/NK failclosed immediately: depth1 has10fixed-depthROMgate loads, incompatible fanout<=4.
- T15 NL/NK producecandidateJSON; maxnewparent-nodefanout4. NL remaininglongrootregp13->p14/l5 arcs166.597/175.59um; NK remaining191.364/351.028/156.033/195.9um. These oldrootregsubtreeparents were retained and need fullsharedspreadrebuild, not anotherad-hocbuffer.
- Independently actualmacroICG->macroclock distances from the inputcensus: NLrp0 656.499um, rp5 569.523, lsl2 513.879, rp1 507.369; NKrp0 547.713, rp5 543.441, rp6 434.757, rp1 434.007. Existingmacro-leafbuffer isatgate+1.5um, so itslastwire remainsunbounded. The currentSPREAD_GEOMETRY census reports node/gate arcs ONLY anddoesNOTinclude leaf->macro/FFsink segments; neveruseitsmaxlegasaPASS. No picture/P&Rreview done forfailedT15; notreadyforCTS.

NEXT (T21 discussion approved forplanningbyQCparent but NOTIMPLEMENTED): fixFULLtopology includingeverymacrobranch androotregleafparent. ExistingmacroICGs mustkeeptheirGEOMPASSplacedxy (enablehopbound). Putregistered-free clockrepeaters AFTER thegate alonglegalmacro-freecorridors to theactualmacroentry; allclockbufferlegs~<=150um andfanout<=4. Macrointernalviewk8/7 plus~7externalrepeaters andpre-gate4-wayfanout requiresTabout21; doactualphysicalhome/census beforechoosingT. RebuildrootFFleafparents throughsameboundedspread instead ofoldp13/p14centroidtree. PreserveequalTOTALdepth accountingmacroview/CTS3, no pads/trims; computeanalyticclockinsertion androot/IO-referenceeventneeds, thenrender+personallyview/GEOMreviewbeforefreshCTS. Parentacceptedthat t7-only fix insufficient; anynewintrinsic clocklatency mustultimatelyusethemeasuredview inatomicparentIO/dieevent, notold693/666 constants. Period833/60-25unchanged. T21source/edit/build didNOTstartbeforereset.

OWNER? None new. No PASS/SIGNED/freezeclaim. Oldfailedverdicts kept.
