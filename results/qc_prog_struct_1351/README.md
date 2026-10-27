# PROG NE2 concrete static placement proposal

Owner Codex GEOM; coordinated Qwen/qk_cores. Existing two routes remain untouched. No new P&R or STA launched.

Actual GRT writer cohort is136 E-side wd_in bits at113.580..126.540um, each INVx3 + DFFHQNx1 pair. Current restoring inverter and capture can straddle upper macro corner; q126 inverter y128.250 versus macro top127.464 and FF y127.170. Read-mux NAND/OA21/INV cores compete immediately east of these producers while output FFs liex345..350; moving only FFs or enlarging another routing halo does not address this competition.

Static allocation from actual instance inventory and actual rows:136 paired writer cells occupy136/179 available two-cell slots in4 columns atx270.648+1.620*c; all pair bodies east of reserved pin strip ending270.618. Pair tops <=126.630, below routing-only corner lower edge127.164 by0.534um. Maximum absolute difference pinY to paircentreY0.189um. MY/R180 gives rail-equivalent horizontal flip toward SRAM. Actual pin-transformation/PG validation remains a builder gate.

Exactly1371 unique per-output mux cores (457 each NAND2x1/OA21x2/INVx1) move into actual free corridorx300..320, near unchanged output Y, staggered across9 lanes at2.16um pitch. Mux-only maximum5um-bin fill is7.64%; the proposal avoids making another narrow combinational wall. Shared control buffers,972 producer/control FFs,457 output FFs and every clock cell remain unchanged.1643 moved cells total.1001 actual nonmoving obstacles respected; static body-overlap checks and row/site alignment pass. No placement-blockage waivers or macro/PG changes. Sparse assignments in prog_static_proposal.json.gz; reproducible allocator takes accompanying decompressed JSON inputs. Personally viewed full and zoom PNG.

This is a source proposal, not timing/routability/PG approval. Before a successor: inspect transformed actual pins/escape demand against actual macro+PG obstacles; implement narrow cohort/group placement using existing master recipe a473c722ce; refresh internal clock plan from moved FFs; independent composed review and normal AP/source/canary gates. Do not start a third route while current jobs run. Preserve old GRT/DRT failures.

Correction: report40=83/zero-clock was inherited baseline timestamp08:19, not the current route2. Retract that current-progress/overlay attribution. Actual report35=744 at13:58, live log subsequently603 dynamic violations. Structural occupancy evidence comes from actual GRT, independent of the inherited DRC overlay. Neither route is terminal.

Actual pin geometry transformed from old native pin rectangles through old/new R0/MX/MY/R180 orientations: all136 paired chains have maximum FF-QN to inverter-A MHD0.091um, and maximum inverter-Y to SRAM-WD-pin MHD12.208um. This confirms the horizontal flip makes the local pair face the SRAM. Pin-transform JSON/script included; full real PG routing-cut capacity remains unmeasured, not inferred from these short distances.
