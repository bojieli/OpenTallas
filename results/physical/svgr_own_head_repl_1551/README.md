# SVGR own shared-head capture candidate — NOT READY FOR PHYSICAL

Base 66d55c026ad. Actual RF3 vC E4 die-hbm-82-svgr/kits/ot_svgr_own_vC/ot_svgr_own_2054dcac0c09 is NOT SIGNED: TT -78.81/1223, FF -18.87/159, slew TT2137/FF1333, DRC0, native LEC EQUIVALENT. No new ECO.

Actual worst slew525ps: OA22x2 _088706_/A1 (also _083593_/A1/_089695_/A2), net23967 from BUFx3 place23968, seven loads, original head_q[2][132] QN. Peer net23685 is head_q[3][132]. RF3 only registered the lane mux output; it retained the shared head-to-eight-lane wire.

HEAD_REPL default0 keeps the shared source. Value1 creates a kept capture per PC per response lane, at the same old edge. All head words and every gnt/valid expression are unchanged; no port or cycle contract changes. This removes shared head-Q fanout, but moves the cost to head-C fanout and clock load. Physical planning must place capture clusters and their muxes together, with local buffers from the skid source. It does NOT solve the separate hbm_fault-to-PC epoch setup path or reset/DRV class. Do not claim whole-form readiness.

Price: IW=283+LB=285, four PCs, eight lanes:9120 capture bits vs1140 old shared bits, net+7980 assuming synthesis removes unused shared captures; ~33.4percent of measured23904 baseline flops. No ASIC area/clock insertion estimate asserted. Same pin cycles, throughput, reset release. This cost is material; no physical launch until the whole source class plus real regions/clock budget are coherent.

Observed GRT images viewed: /tmp/codex-hbm-types-1551/svgr_own_vC_grt_density.png and floorplan.png (actual5_1_grt). 129.6x432um, fill.282, no macros; red E/W face density bands beside sparse middle. Not a congestion proof. New candidate requires its own proof and image before one PLACE.

Proof scope: future literal extracted head-capture/mux class first, then full native kit LEC. No current proof result claimed. No inherited kit input edited.

Literal capture/mux class benchmark actual I1 normal4GB2T unit4190675-1794096478: M0 10000cycles/9998activegrant edges, all2280outputbits0mismatch; default-off also0. Wrong PC/lane capture-bit rotation mutant4926output-different edges, bypass-capture mutant9998output-different edges. Exact bench2.log preserved. This is the literal changed capture/mux class with arbitrary full-word input/grants, NOT full native-controller or whole-kit equivalence. The first ORFS-container attempt failed127 because image lacks Icarus; host /usr/bin/iverilog/vvp under admitted cgroup used for corrected attempt, failed log preserved remotely.

Existing GRT coordinate budget for final-netlist names: worst BUFx3 place23968 (19.872,213.165) to OA22 sinks with x18.9..19.602, y41.985/158.625/190.215/41.985/45.225/100.305/123.255, mapped by combinational netlist graph to lane_d_q[132] lanes0/1/2/4/5/6/7 respectively. 171um driver-to-lowcluster,148um loadspan. Coordinate stage is EXISTING5_1_grt, not6_final. Two cheap groups must follow real spatial regions, not naive lane0..3/4..7; grouping still requires all-bit/clock/region review. Parent rejects8-copy physical without a tighter budget. Candidate stays source-only; no full proof/PLACE/CTS/STA.
