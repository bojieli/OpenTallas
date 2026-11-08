# SVGR own shared-head capture candidate — NOT READY FOR PHYSICAL

Base 66d55c026ad. Actual RF3 vC E4 die-hbm-82-svgr/kits/ot_svgr_own_vC/ot_svgr_own_2054dcac0c09 is NOT SIGNED: TT -78.81/1223, FF -18.87/159, slew TT2137/FF1333, DRC0, native LEC EQUIVALENT. No new ECO.

Actual worst slew525ps: OA22x2 _088706_/A1 (also _083593_/A1/_089695_/A2), net23967 from BUFx3 place23968, seven loads, original head_q[2][132] QN. Peer net23685 is head_q[3][132]. RF3 only registered the lane mux output; it retained the shared head-to-eight-lane wire.

HEAD_REPL default0 keeps the shared source. Value1 creates a kept capture per PC per response lane, at the same old edge. All head words and every gnt/valid expression are unchanged; no port or cycle contract changes. This removes shared head-Q fanout, but moves the cost to head-C fanout and clock load. Physical planning must place capture clusters and their muxes together, with local buffers from the skid source. It does NOT solve the separate hbm_fault-to-PC epoch setup path or reset/DRV class. Do not claim whole-form readiness.

Price: IW=283+LB=285, four PCs, eight lanes:9120 capture bits vs1140 old shared bits, net+7980 assuming synthesis removes unused shared captures; ~33.4percent of measured23904 baseline flops. No ASIC area/clock insertion estimate asserted. Same pin cycles, throughput, reset release. This cost is material; no physical launch until the whole source class plus real regions/clock budget are coherent.

Observed GRT images viewed: /tmp/codex-hbm-types-1551/svgr_own_vC_grt_density.png and floorplan.png (actual5_1_grt). 129.6x432um, fill.282, no macros; red E/W face density bands beside sparse middle. Not a congestion proof. New candidate requires its own proof and image before one PLACE.

Proof scope: future literal extracted head-capture/mux class first, then full native kit LEC. No current proof result claimed. No inherited kit input edited.
