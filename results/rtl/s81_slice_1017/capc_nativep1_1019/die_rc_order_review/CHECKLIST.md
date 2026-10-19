# ROOT review request: fresh original2647 CAPC after RC-order repair

Source b0f1fd5a97c974f0fa5b2e3e05e7dfb34903bb8f; canonical framework18b8c357d including all49 helper overlay paths. Same RTL PINPIPE1, original345.6um square outline, all child placements, pin locations, clock knobs and explicit margins/budgets. No CLK10 knobs reused. Guard admission retains the original padded source-pinned receipt, solely for eligibility; the measurements below are this candidate's own fresh CTS ODB.

- Coarse gate WARN, zero failures and zero route overflow. Standard428.2um² plus hard45909.5um²;39% standard fill. Hold repair820 buffers versus3645 before calibrated-RC reference ordering repair. Hold starts-9.45ps under refreshed calibrated reference rather than stale-64.19ps.
- Own fresh native TT launch110.84912ps<=220, capture106.91663ps<=190, zero combinational paths and zero violating bits. TT boundary mean774.0ps, range759.0..795.2 (spread36.2); FF606.1ps,592.5..626.3 (spread33.8). Child-inclusive maxima807.6/667.2 are not the boundary means.
- Own fresh FF output all-table minimum54.21805ps>=25. All1173 nonclock source bits exactly match both models:722 inputs/451 outputs; no missing, unconstrained or combinational data pins. Rails excluded only when absent from source and arc-free.
- Both floorplan.png and density.png viewed. Original three hard children remain separated with open standard-cell bands; no dimensions or keepouts reduced. Actual macro PG/route and native clock assumptions still require normal downstream acceptance.
- Golden functional proof remains1280writes/7446arrivals, coherent W+2/A+1 and two-stage local reset; no RTL change since that proof. Native FF does not independently validate functional protocol.

Review images: physical/ref_tile/s81sl_capc_p1_die_rc_order/gate_layout/floorplan.png and density.png. Native files in sibling die_rc_order_native_cts and die_rc_order_native_ff. remote_native_sha256.txt binds both probe scripts, outputs, exact archived gate spec and4_1_cts.odb on saved fresh102231 run. Gate source_binding independently hashes archived source/parameters/children.

REQUEST: ROOT inspect PNG/checklist and authorize next qualification/review step. No REVIEW.json, submit, view adoption or main merge has been performed. This is CTS placement-RC diagnostic evidence, not routed native/die-link qualification; full accepted model/die schedule/clock linkage remains owed.
