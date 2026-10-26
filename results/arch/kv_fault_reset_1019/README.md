# GEN7 fault reset branch candidate — not installed or qualified

This successor rebases the earlier GEN4 fault proposal onto GEN7 source
`4db097403`, using the corrected canonical `gen7_bind_r1/die_bound.v` and its
actual placement, element LEFs and forwarded lanes. The inventory still has
356 real sources (351 sticky landing faults, four KC pulse sources and the
existing upstream hub input), 1,351 added resettable fault joins and 85 reused
payload bits. The independent data check retains a 180-cycle maximum logical
fault path and a 400.2035 µm maximum same-clock data edge. Transport ages are
conservative candidate ages, not installed native phase measurements.

The new reset planner changes only the proposed fault cells' reset assignments.
Every old reset load and edge remains unchanged. It uses exactly traced
same-root, same-clock existing outputs with spare fanout, places new closed
12.96 × 12.96 µm `qkd_rlys_1` reset distribution stations around the old case
and proposed fault cells, and reports each new target's changed root-relative
depth. It does not pretend to preserve the inherited target depths that the
earlier necessary-bound analysis found impossible for 385 targets.

The candidate has 1,161 new reset stations, adding 195,003.4176 µm²
(0.195003 mm²); with the 630,322.56 µm² fault cells, the combined addition is
0.825326 mm². Independent native-pin geometry and old-plus-new fanout checking
passes all 1,351 target pins, with maximum reset edge 403.212 µm and maximum
total seed/branch fanout 30. This establishes geometry and conservative load
counting only. It does not establish clock distribution or loaded reset timing.

The final sticky cell receives a separately delayed reset branch. Its proposed
assertion and release depth is 273 edges from `host.die_rst_n`, versus the
inherited 11 edges: +262 reset/boot edges, or 218.33 ns at 1.2 GHz. Functional
data paths gain zero stages from these reset branches. The delay is chosen
after accounting for every upstream proposed reset assertion, source-clear
depth and downstream logical fault path, plus an **explicit diagnostic**
cross-root assertion-skew hypothesis of 64 cycles and two model edges. No
measured receipt currently establishes that skew hypothesis. Root-relative
depths from different regional roots are never claimed to be a common epoch.

This 273-edge branch exceeds the existing regional `IGNORE=255` setting.
The current boot and host admission calendar cannot be reused unchanged:
the complete POR flush, all root epochs, host reset pulse propagation, new
branch releases and next-admission guard require explicit proof and pricing.
Existing `HOLD=128` alone is not the clear proof. The proposed late final
sticky assertion removes old accumulated state only after the conditional
upstream stale-fault drain bound; its later release must also precede admission.

`kv_fault_reset_clear.py` models the full graph, including all transport stages,
all sticky feedback and all reset target cohorts. It starts with stale ones
everywhere and holds each source high until its modeled actual reset assertion.
It checks 12 root schedules, then each of the 356 source pulses after reset.
Missing final reset, missing KC pre-sticky reset, early final release and
missing source clear must each produce a stale-fault resurrection witness.
This is a cycle-model proof, not an RTL/CDC receipt. In particular the old
`existing_ufh` upstream graph still needs its own actual clear-on-reset proof;
its clear at the consumer's local reset is an explicit unresolved assumption.

The emitted review fragments contain actual reset wires, relay instances,
placements and the updated proposed fault reset ports. They are not installed
in the active case. Clock pins name original clock nets, but **no physical
clock tree, native phase/calendar, reset STA, POR or host admission receipt is
present**. All reports retain `qualified_release=false`. No root setting,
functional cutoff, STATUS age or continuously live health behavior changes.
The compiler still separately owes the full functional cutoff-to-STATUS path,
including upstream joins, AFR, TX, landing and link. No faults are masked or
cleared at that cutoff by this proposal.

Inputs, candidate, exact reset manifest, proposed branch graph and review
fragments are retained under the matching compressed files. Actual fleet
outputs live at
`ot-epyc5:/srv/opentallas-scratch/claude/kv-fault-reset-1019/gen7`.
The first route attempt's adjacent-station spacing refusal is preserved as
`reset_branch.log`; the corrected routing pass is `reset_branch_r2.log`.
The initial clear-model receipt is retained separately as `reset_clear_model.r1.json`;
the final model strengthens nonsticky stale-source initialization and includes
the fourth missing-source-clear mutant.
