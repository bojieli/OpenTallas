# G5f post-relay fault capture source proposal

Exact baseline: d502ea9ae, dv2f20g5 die SHA771ed19400e3e7fba0320409ee305cff9018b005c150eaa6b265c281e7a76ca2. The fresh actual inventory has 425 instance output ports / 498 unused bits / 64 clock nets. Capture must distinguish reset leaves too: 340 (clock, reset) pairs, producing 344 local capture nodes and 1,874 flop bits for N<=16 and N+4 state per node. The prior clock-only planner may merge sources whose reset releases differ.

post_relay_fault_capture.py consumes actual source definitions and emitted die connectivity, refuses stale master/width/clock/reset/connection/classification/duplicate bits, reuses existing partially consumed fault nets, and proposes explicit hookups for open outputs. The fragment contains source-clock-native qfd_fault_or captures and separate domain roots. It is an insertion proposal, not emitted GEN or qualified hardware. Nine focused checks pass.

The actual bound sys_face source has NO obs_fault input. The tool therefore records actual_sys_face_obs_fault_input=false and die_emission_eligible=false; it invents no STATUS sink. Geometry/placement/native pins, reset-tree fanout regeneration, bounded cross-root landed transport, full calendar and functional STATUS proof remain owed. The added two-stage local reset release also needs causal startup pulse coverage: a source fault before capture release must not be silently lost. No first-cycle fault coverage is claimed.

This proposal was preserved when ROOT prioritized the GEN5 shared clock-tool projection. No current GEN, source-owned Claude WT, running fleet job, schedule, model default or physical gate was changed.
