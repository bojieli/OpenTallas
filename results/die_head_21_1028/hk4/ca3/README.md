HEAD HK4 fresh regional clock and CA producer

The current data source is ../plan_spine_raw_rx_tx.json.gz:351parts,21types,327regions. Four ribbon RX/TX type identities replace two equal-geometry masters because their landing masks differ. G0C has0errors,0pending-view,21/21clean types. No data cycles or external pin positions changed.

The reviewed physical clock is local2: neighbor-forwarded spine/column forks with balanced local Htrees, inv2/NDR/100umleaf/200umrepeaters. Actual735tap+10848cell edges pass405um (max339.72). TT/FF GRT50 both0overflow,58082nets,49.803746mwire. Worst327-region spread87.61737/74.34264ps is a geometry diagnostic, not release signoff.

CA3 uses every physical endpoint pin's nearest-tap set including ties and all selected tap-pair hulls.427external rows receive the shared actualrelated TTsetup/FFhold interval hull;0missing,0unbound,0withoutmeasuredfall. Only the exact24same-region spine-inner links are excluded from CA and remain intra-region timing ownership. inv2 spice_edge, CPPR-LCA, tableOCV/shared regionaldroop, actual per-type hd_tile ring profile; other localclock latencies remain explicit450TT/380FF budgets. All427DEPTH4,0below100ps,worstguard113.0ps,MC2000chips0violations.633STARTedges clean633, plannedminsyncdistance142.1ps.

The producer emits307virtual STARTstages/1061flops, planned next to actual clock cells (max9.18um), plus patchedclocktapports and real START RTL. These physical STARTflops and the full landed net vehicle MUST be included in the next measured route. CA3 stage clocks still use the planner's explicit initial-stage estimates. No final release/freeze/SIGNED claim.

ready.tar.gz preserves measuredclock graph, physical pin assets, CA3 plan/bind/straps/regiontable, proof and STARTproducer. The remote original is intel2:/srv/opentallas-scratch2/claude/codex-head-hk4-localgrt2/ca3. Earlier failures retained separately: legacyFT layer lookup; absent physical-LCA metadata; mixed RX/TX landingmask; old ASCII pathalphabet;24physicalshim endpoints omitted fromSTA hull. Each cause is corrected in the owned producer, which now refuses incomplete full HEAD hulls.

reset_offsets_rx_tx.json publishes raw reset wavefront only:351parts,maxrelease91,maxhop378um,0unreachable. reset_start_offsets_rx_tx.json explicitly separates reset_release from start_offset:null; ca_origin_nominal is planning metadata and is not an absoluteSTART offset. Do not fold the root64settle or historical broadcast reset/START offsets into a measured CTL START authority.
