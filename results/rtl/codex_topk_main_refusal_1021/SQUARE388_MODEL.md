# TOPK388.8 square source/model — no gate

This is a concrete generated source kit, not a qualified view, physical fit, or approved adoption. `physical/ref_tile/s81dvbk_selcpn_e` keeps the exact cb73 control RTL/public ports/params/defines and fixed source calendar. The earlier MAIN clock/GRT/pin-capacity refusal is immutable in FAILURE_PACKET.md. No c2 view or control proxy is assigned to the successor.

The6072 functional+clock pins require at least1518um perimeter at4pins/um. A square must be at least379.5um per side;388.8 is the next43.2-lattice square. Failed geometry had6216 pins only when144supply shapes were included; the new physical supply count/geometry still needs its actual gate. Final functional face counts are S1508/N1509/W1544/E1511, respectively3.879/3.881/3.971/3.886pins/um. Whole named ports are used: no bit aliases, masks, grant or RTL interface change.

|Face|Whole named bundles|Count|
|---|---|---:|
|S|fs0_0,fs0_1,fo0,fs1_1,fs2_0,t_cr_s|1508|
|N|fs3_0,fs3_1,fo3,fs1_2,fs2_1,t_cr_n|1509|
|W|rst_profile,ck,fs0_2,fs3_2,fs1_0,t_c_s,t_c_n|1544|
|E|fo1,fo2,fs2_2,vd|1511|

S/N far-quarter bundles+credit occupy1.08..235.44um (932pins over234.36um); the central288/289-bit group occupies235.44..307.8um; fs2_0/fs2_1 use307.8..387.72um. This partitions west-entry and east-approach traffic. W/E use1.08..387.72um, with ck constrained on W at194.184..194.616um beside the new vertical register/macro mass. W is tight: after reserving the0.432um clock band and1.08um corners,1543 nonclock pins have capacity1544.832 at4/um. Actual PPL, pin-flop placement and PG access remain required.

The12 identical P192 SRAMs stay R0 at x43.2/129.6/216/302.4. Rows move from y43.2/129.6/216 to43.2/172.8/302.4. With the existing6.48x2.16um halo, vertical clear channels grow42.12->85.32um; horizontal clear channels remain22.032um. This is a concrete channel/topology change in response to the boxed local queue net, not an unchanged retry. Old placed areas projected into the larger outline would give28.47% fill; that is not a new measured area. New area is151165.44um2, +33592.32 (+28.57%) over failed388.8x302.4. The pin perimeter, not a minimum-logic-area claim, motivates this outline.

The one ck source, route770ps overconstraint, signoff833.333ps,60/25ps uncertainties, sink-clustering/repair/0.75 derate and reset profile are unchanged. The new explicit topology option is `-balance_levels`, supported by the actual installed OpenROAD26Q3 command help saved in the packet; no design/gate was loaded for that API check. Acceptance still requires actual TT/FF pin-flop spread<=80ps plus timing/native/PG/GRT checks. Internal all-flop spread is diagnostic, not a blanket80ps rule. No clock-count or insertion waiver is inferred.

The parent reservation preserves all existing corridor widths and the86.4um north band. Control sits(216,1555.2), size388.8square. q0/q1 remain at y43.2/864; q2/q3 move to1987.2/2764.8. Glue moves up216 to(648,1771.2), aligned with the control's north edge; this preserves the critical north lane's seven-segment reach. North rung relay moves to(129.6,3456), using its actual25.92x17.28 view. The nominal parent grows907.2x3283.2 ->907.2x3499.2 (+216height), not the earlier smaller arithmetic that omitted the retained north band. After this nominal parent, TX540 and one43.2gap, the4190.4 release band has only108um left for actual VMUX and further bodies/corridors. No full-slot fit is asserted.

`verify_square_model.py` uses the exact published quarter LEF0d4ba50ed and real glue pins, prospective whole-port face-interval endpoints, site/row snapping, and real hard-body rectangles. It checks12348 paths (all7204 quarter lane/control/selected/credit signals, with both control face extrema) and returns max segment bound398.927572um including a universal0.162um anchor-snap allowance per endpoint, local pin-bank distance<=21.6um, no reference anchor inside a macro body. The worst is q3lane514. The already-priced single VD relay has max324.594um. Seven D2/K1 segments per direction,14edges, XR34/XD17, VD+1 and tail796 are unchanged; no extra issue/ACK/return stage is hidden.

Central east approaches route via the macro-free43.2um side gap and existing N/S corridors; the two central status chunks have dedicated face intervals. Preferred-direction core-band raw capacity is2560.25 tracks. Entry-cut lower bounds are2016 wires for a far bundle,1252 for the combined N east approach and624 for S. These are not an all-cut or simultaneous routing proof, and they grant no extra layer. The224 existing seam bodies, declared238532 landing FFs plus509 parent reset FFs and514 VD FFs still need real allocation/fences/clock/reset/pin access. Target coordinates are proposed face bounds, not a new control LEF. No hard-child alias, parent fit, CTS or physical closure is claimed.

The kit generated successfully with only a missing-area fill warning. Earlier sparse-only helper/read failures are retained as source-preparation logs. No gate, native rerun, normal qualification submission or main merge was admitted for this model. ROOT chooses the next action after reviewing the exact failure and this source model.
