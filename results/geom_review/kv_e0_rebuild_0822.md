# E0 corrected-flow rebuild review, 2026-10-29 08:56 PDT

Viewed originalactualrouted floorplan,density andworstholdpath: results/kv_e0_rebuild_0822/{floorplan.png,density.png,paths_zoom.png,paths_ff_hold.txt}. Source intel2 kv-kits-16-1028/kits_heads/kv3_head_eighth_e0__216x216, commit5513f9b01e/kitaf740d2710b8ac78. Successor must retain everyRTL/pin/outline/clock/resetentry and macroplacement field exactly; this review is not for a structuralvariant.

Verdict PASS-COND one fresh same-geometry build with correctedFFrepair staging, then actualpost-routeFFhold repair under source6be8c010c. OldNOTSIGNED evidence retained.0macros/no walls, continuousPG stripes,59.3% stdfill broadly uniform withsmall isolateddensity hotspots and availableperimeter.216umoutline keepsdatareachlocal; widepins S/E are adjacenttofacecaptures, no slivers. Rootclocknearcentre; measuredrelatedskew34.3/31.2ps andDRC0/ant0 show no structuralclock/routingfault on the unchangedoldvehicle.

Measured failure is FFinputport->capture FF: u_kt__kp_in[72] to u_u_kt.u_kt.kp_r[72], actualcapture215.52ps versusboundFF202.5; data200.78 vsrequired242.48, slack-41.70. ThreeexistingBUFx2stages are insufficient underactualroutedclock. CorrectedFF-onlyECO uses realRC/frozenclock anddeclared15psmargin, no vclkrebind. TTsetup+54.94 andonly1slew violation retained aslimits; re-signonactualfinalview required.

Capacity is valid: raw193913synthASAP7cells,191088placed/195372CTS/213841routedstd.433264totalincludes219423physicalfillers and is not a >400kstdcellrun. Originalrun/results wasremovedbyautopilotafterreview, sofreshbuild is necessary. ExistingLEC EQUIVALENT receipt andsourcecopies remain; reuse onlyafterexactsource/synthmatch checks, never rerun anotheragent'sworktree.
