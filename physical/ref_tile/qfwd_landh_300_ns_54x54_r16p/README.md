# SAFE-QW-LAND300r16p design review

1 PASS: ring input captures and registered outputs; k3face flops. Receiverreset2stages explicitly inRTL; writeepoch1face stage after existing laneepoch. +1write/+2read bootedges =>Klegacy-1mod8, no steadystatecapture added.
2 PASS:54.408x53.976um, diagonal77um<405um.
3 FIXED:19kept regions<=16bits, LOCAL4slot-valid and onehot write/read selects, perregionwriteepoch/secondresetstage/warm. Globalrs0drives20secondstage flops; writeepochrawdrives20firststage flops. Measure synthesizedfanout before qualification.
4 FIXED: registeredonehot4slot maskedOR, constant slotaddresses. Check TTdepth and directlytimedcrossing slack.
5 PASS:1200ringdata+300outputs+~300controlflops<2048bits, no runtimeindexed floparray.
6 PASS structure: no macros/powerislands; onefullstdcellband; aspect1.01. Facepins301/53.976=5.58/um. Outline from~1kum2synthesis+clock/IOoverhead and pinminimum; recordactualCTSutilization.
7 FIXED: no falsepath/MCP; safe_land_clocks.tcl directquarterTsetupenvelope charges60ps+0.75T uncertainty,25pshold unchanged, actualCTSskew charged. io_hold_margin0.03. Measure TT/FFspread<=80ps and neighbourmatching.
8 PASS static:4slotring, nocredits/backpressure, unchangedsteadycaptureedges. Ksafe=Klegacy-1mod8 bootprice inlane_groups/reset_calendar_audit. ParentmustproveTT/FFcompensatedreadage[0.25T,3.25T],overwrite>=0.75T orrejectbinding. sample_window.json25,088checks.

Retains priorr24synthesis/timingfailureasimmutablehistory. Neverqualifythiscandidatefromhistorice1native-onlyreceipts.

Assertionobservabilityprice: epoch/valid captured toreceiverroot without mux; stickyfaultcompares previousreadtag1cyclelater. No data/outputcapture latency added. Total sequentialstate~1.84kb, under2kb. Previousr16 epochmux SSfloorplan-75.35ps retained as failure evidence.
