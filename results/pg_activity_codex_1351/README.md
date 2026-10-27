# PG-ACTIVITY-2 collection and QC actual-cut result

QC canonical interior deck uses 2972.16um square, 150um bumps, 70um finite pad plates, VDD drop + VSS bounce, 5.1437W region-model load, and a450um open-edge keepoff. Existing completed light/wide jobs give32.902mV and9.715mV ABOVE M7. They do not include lower-metal drop. Full-die jobs remain independent inherited work, not used here.

The exact current R28 net_holes from18c6286d88387ac812ac0a74920fa8c4f275e1b5 were clipped into the SAME interior deck. All intersecting holes span a whole selected window stripe, checked before generation. Post-pdngen removal deletes19M8 +4M9VSSstripes and14368intersectingVSSvias; no other nets or loads change. Both rails remain connected. Unitoth-ubuntu-3659867-1793134736 EXIT0 gives34.094mV, delta1.192mV. Only0.906mV remains for belowM7. Full PG closure is NOT established.

Rendered grid reviewed beforelaunch: actual cuts preserve the orthogonal PG network, no enclosed islands. The actual rail connectivity checks confirm that condition. Source deck is intel2:/srv/opentallas-scratch2/claude/codex-pg-act2-1351/qc_cut. Image is qc_cut_plan.png.

HBM measured activity collection found originalSM trace unit1788511 ended143, withoutHGI_SM_E2E PASS. Case0 INT8 K512/M7/P1 retired571cycles and advanced withoutreportederrors; case1 was partial. No DS cases were reached. Existing matched-activity power reports fromintel1 had alreadycompleted13:28; they are collected here, not rerun. Placed half densities are0.31947/0.31755W/mm2 for the two windows. BDC CTS/place uplift gives estimates0.61046/0.61406, explicitly NOT provenSMbounds: RP3half views have essentially no realclocktree and are not the selected current four-hard hierarchy. Do not adopt these as qualified production power or claim DS measured IR. No new simulation/VCD was launched.

Currentmain still lacks HEAD5 finitepad/edgefill integration in die_trial (defaults4um pointsource); canonical passing deck and eventual actualdie emitters must use the same explicit supply model. That sharedsource integration is separately owned.

## Actual lower-core and minimal grid follow-up
Actual SIGNED VMR4KPG at77013e5059, unchanged readonly6_final.odb, has M1/M2/M3/M5 only (noM6/M7). STRAPS source therefore feeds the actualhighestM5; earlier requestedM7label was corrected after actuallayercensus. At canonical0.5823W/mm2 normalized byfunctionalcell+macroarea,23860cells+2SRAM,total31.515mW, co-locatedrailmax3.544mV. This is a conditional lower-core calculation, not measuredactivity or completebelowM7. It makes the .48cut composed bound37.638mV, which is not an admissible <=35 result.

One minimal candidate M9.576/M8.48 at8.64pitch, samephase and150/70supply, actualcuts grown towholeM9stripewidth: unit4061819 EXIT0/bothrailsconnected gives32.075mVaboveM7, +VMRlowercore3.544=35.619, stillfails chosenbasis. Next model-drivenM9.672 samewide-spacingregime unit4162362 EXIT0 gives30.403mVaboveM7, +3.544=33.947, leaving1.053mV forM6/M7. This is conditional, not a fullPG PASS or planadoption. Both widths cross ASAP7 .49975um wide-PGthreshold: .5umspacing atPRL>=1.79975 must be charged by clockplanner; metalfraction alone is not trackcost. Source/currentgrid adoption belongs toONEQCevent.

Actual macro-free coll_ftm finalPG fullbelowM7 calculation continues asunit3832916; its DEF verifiesM1-M7 presence. It uses80,260functionalcells and0.672457W atcanonicaldensity over1.154829mm2. No source/timing build or oldODB edit.

Current finitepad/edgefill tool source was subsequently integrated by root(main e3497c17), superseding the base5b source gap above. CurrentHBM C15outline differs from oldsurveyframe:150pitch70pad/edge_margin35 produces189columns(first99.84um) and124rows(first45.72um), not old72.12um headline. Do not substitute oldgeometry or partialINT8 map as currentdie qualification.
