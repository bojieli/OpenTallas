# Reset-landed frame binding source contract

SOURCE CONTRACT ONLY. Existing intended gates at source21b97190e continue. No engine RTL, geometry, test or equivalence campaign was added.

Inventory:36 normal h9,24 h9_MX,12 h10. Actual tops are col_h9_l4_lp and col_h10_l4_lp with ck_r0/ck_r1/ck_r2, not the old modules with clk/cr/cr_s. bind_contract.json gives exact source, kit, compiler-record and pending-view paths and every port width. Real die source entries must be supplied for all three regional roots; a port rename or tie is not a source/domain contract. Each xk[k] is also a real forwarded clock, separate from regional CTS, whose role must survive the actual exported timing model.

Actual frame_wrap.emit_mirror emits exactly one base-master child with all ports passed through and INSTANCE unchanged. frame_l4.py transforms that wrapper into col_h9_MX_l4, whose only child remains col_h9_l4. There is no separate MX logic or bit permutation. Consequently, a separate MX engine or LP implementation is not inherently required: use the ordinary h9 LP physical master with one MX geometric transformation. Explicitly replace the module/view binding, preserve bit names and frame programme/image identity, and transform LEF pins and clock-entry coordinates. If the plan already applies MX, do not apply it twice. Keep r0/r1/r2 labels: reflection moves a region's coordinates and does not rename its clock.

This is a structural reuse argument from the actual wrapper source, not equivalence between the old non-LP and new LP bodies under different clock/landing contracts. The existing normal LP receipts cover its landed body; its physical view is still pending. The old MX wrapper cannot silently bind against the LP view: its old module and clock ABI differ.

All entries retain bind_ready=false and regional_clock_net_mapping=null until the die lead supplies actual graph entries and matching views exist. No reset or clock source is invented. Source scope is current rf3rlfs1 bindings; CPR/Q-only schedule rebinding is separate.
