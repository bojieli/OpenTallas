Class geometry successor, 2026-10-21

The actual B source GEN classgeom0030 failed on rly_dv_ch_E1_ar_ard_0,
qfd_landh0_600_EN_104x106: no legal site within strict actual 405um reach;
last obstacle dvs_E2. B had expanded E0/E1, leaving E1/E2 at129.6um.
The failed immutable ep6 directory and out.log remain preserved.

Source3403b5c23 adds explicit existing-channel expansion. The single successor
reserves E1/E2gap259.2um by adding129.6 and translating the replicated array
west129.6. W services stay fixed; western service clearance consumed129.6.
Die32983.176x24288.824 stays inside33000um guard, outline area increment0.
Two independent104x106 class footprints and12.96um row/endcap slots need246.88um
of channel width. This is a physical reservation; actual GEN still decides legal
native outline/pin placement. The floorplan transform inserts no explicit pipeline stage. GEN rebuilds real
relay topology, so final stage counts and token-age deltas remain pending actual
relay-table derivation and calendar recompilation. Frozen0125 metadata zero
was a transform-only statement and must not be read as final age equivalence.

classgeom0105 failed at the actual core-feed bump because retaining its old
17409.6,12096 coordinate overlapped shifted dvs_E0. The next single successor
classgeom0125 moves the real package bump to17280,12096 (west129.6), retaining
its86.4um offset to E0. CORE_FEED_XY drives the real clock planner, and source.json
records this movement. No reach limit, source width or class timing changed.

setup_channels.py and setup_corefeed.py preserve the concrete input recipe.
classgeom0125 reuses the immutable0105 source via src symlink and uses fresh
absolute output/log paths, so neither predecessor source nor outputs are mutated.
Canonical ew595_r16 remains diagnostic: old sysface physical image mask,
reset-capture calendar HOLD and missing RoPE/OVL successor parents preclude a
paired release claim. Existing class functional evidence is reused; no new
unit/audit/proof campaigns were run under the owner directive.
