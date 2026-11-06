S81 station native split — implementation WIP, 2026-11-06

Current retained source: intel1 dedicated scratch2
/srv/opentallas-scratch2/claude/codex-s81-split-1106/mapped_controls/
child_w.v, child_e.v, parent.v, split_clean.json, abi_map.json,
source_sync_inputs.json, pin_anchors.json, captured.json and clock_capture.json.
Original B51 3_place/4_cts ODBs and exact source constraints are retained one level up.

Exact native graph conservation PASS:188969 original functional cells; west98134,
east75637,parent15198. All53074 original FFs are inside401 complete native
FT/landing/reset/collector/monitor groups; parent has0FF;0added cycles.
The copied outrelay remains distinct. Source clocks bind to exact actual CTS roots;
no source clock/root/reset/age rewrite or cell pruning. Source immutable kept JSON SHA
082685115cbcaff28ec49ebf3e0caab50671374a06fe5181b7adb1d1115517e5.

controls_pose.json + station_controls_pose.png: plan-owner PASS-COND for root/pin
preparation, not route. All child FFs packed on native grid, no overlaps. Independent
all-combinational mapped audit:103986 FF endpoint pairs,0over402.84um; original
baseline19over(max414.018). Clock/primary-port reach is separate.

Source timing SDK opt-ins: canonical tap_window_port_ps, landed_clock_inputs,
source_sync_inputs and exact native_clock_pins. Default kits unchanged. Actual
3040 source-sync inputs retain forwarded clock and166.6max/80min, including runtime
IO-hold replay. Wrong-clock/removed-bound/missing-root mutants rejected.47existing
SDC/ring tests pass after sparse dependencies were materialized. Literal get_ports
selectors now use an exact index instead of quadratic regex scans.

ROOT ruling: retain86 parent M7 source sites/frames;89child entries are46W/43E,
with clk_t19/clk_t2/clk_t62 shared. In-lot source sites remain exact. Explicit secondary
branches move child entries at most44.928umW/94.528umE. Root-to-FF corners max334.23W/
240.43E. Native M7 pin dimensions retained. Publish honest actual M7 clock/PG OBS;
no M8 child pin and no OBS6 concealment. Parent clocks use existing M8/M9 authority.
Actual branch arrival/load, common-source frame and expanded child clock models
remain parent composition obligations before activation.

Current next work: registered data pin packing/seam capacity, exact89 M7 entry
construction and child GEN/PG. All child signal pins have native register anchors;
3454 direct cross-child bits can share seam Y. Native child private P&R awaits
full pin/root/access review and ordinary gates. No parent route before signed children.
No hold release or SIGNED claim.
