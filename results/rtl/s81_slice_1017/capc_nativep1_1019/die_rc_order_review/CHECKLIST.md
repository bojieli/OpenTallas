# ROOT review request: fresh original2647 CAPC after RC-order repair

Source b0f1fd5a97c974f0fa5b2e3e05e7dfb34903bb8f; canonical framework18b8c357d including all49 helper overlay paths. Same RTL PINPIPE1, original345.6um square outline, all child placements, pin locations, clock knobs and explicit margins/budgets. No CLK10 knobs reused. Guard admission retains the original padded source-pinned receipt, solely for eligibility; the measurements below are this candidate's own fresh CTS ODB.

- Coarse gate WARN, zero failures and zero route overflow. Standard428.2um² plus hard45909.5um²;39% standard fill. Hold repair820 buffers versus3645 before calibrated-RC reference ordering repair. Hold starts-9.45ps under refreshed calibrated reference rather than stale-64.19ps.
- Own fresh native TT launch110.84912ps<=220, capture106.91663ps<=190, zero combinational paths and zero violating bits. TT boundary mean774.0ps, range759.0..795.2 (spread36.2); FF606.1ps,592.5..626.3 (spread33.8). Child-inclusive maxima807.6/667.2 are not the boundary means.
- Own fresh FF output all-table minimum54.21805ps>=25. All1173 nonclock source bits exactly match both models:722 inputs/451 outputs; no missing, unconstrained or combinational data pins. Rails excluded only when absent from source and arc-free.
- Both floorplan.png and density.png viewed. Original three hard children remain separated with open standard-cell bands; no dimensions or keepouts reduced. Actual macro PG/route and native clock assumptions still require normal downstream acceptance.
- Golden functional proof remains1280writes/7446arrivals, coherent W+2/A+1 and two-stage local reset; no RTL change since that proof. Native FF does not independently validate functional protocol.

Review images: physical/ref_tile/s81sl_capc_p1_die_rc_order/gate_layout/floorplan.png and density.png. Native files in sibling die_rc_order_native_cts and die_rc_order_native_ff. remote_native_sha256.txt binds both probe scripts, outputs, exact archived gate spec and4_1_cts.odb on saved fresh102231 run. Gate source_binding independently hashes archived source/parameters/children.

REQUEST: ROOT inspect PNG/checklist and authorize next qualification/review step. No REVIEW.json, submit, view adoption or main merge has been performed. This is CTS placement-RC diagnostic evidence, not routed native/die-link qualification; full accepted model/die schedule/clock linkage remains owed.

## ROOT-requested internal driver and placed-stage census

The exact same fresh CTS ODB was read without mutation. driver_reach.tsv records all8207 non-PG nets/17604 placed pin-shape endpoints and9397 driver-load pairs: zero undriven or multiple-driver nets. Worst individual net farthest-bbox-corner Manhattan upper bound165.227um. register_pins.tsv records all1177 clock/1956 data/1759 output/26 async STA register pins, including hard-child abstract boundary roles.

stage_reach.py conservatively joins every combinational instance input to every output, stops at sequential data/async inputs and hard-child boundary inputs, and launches from source ports, sequential Q and hard-child outputs. Exact escaped OpenDB bracket names are normalized to STA names. All2481 launch boundaries reach at least one sink, all2509 capture-boundary geometries are present,2495 complete boundary-stage pairs result. Worst farthest-bbox-corner Manhattan span386.651um is reset_l1/QN→u_core.g_hard.u_te/rst_n; zero stages exceed405um. Clocks are independently covered in the net census, not traversed as data; hard-child internals require their own accepted evidence. Source/native boundary1173-bit census remains separate.

This bounds placed endpoint reach. It does not assert routed wirelength, RC timing, PG connectivity or routed parent qualification.
