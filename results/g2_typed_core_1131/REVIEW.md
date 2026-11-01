G2 ordinary hard-core insertion policy

Current H0 and L2 kits both declare core.json clock_contract.kind=hard_core_latency, ruling COORD10-24, target_applies_at='parent partition tap (tap_balance / early core tap subtracts the core insertion)', measured_in='KIT/signoff/signoff.json core_latency; views <module>.core.json'. Their boundary_guard_context.json points to that exact core.json. H0's master slice describes only the existing interior clock entry; it has no core_tree. L2 has no master slice.

The signoff reader already defines this typed contract as publishing measured intrinsic insertion rather than meeting the partition-tap target. The legacy G2 gate instead defaulted to the 20ps partition/model band, stopping H0 at TT276.88 (setup+9.01, FFhold+27.57/+39.62) and L2 at302.92/304.89 (setup+95.03/+91.67, FFhold+26.69/+40.93).

The shared selector uses the existing INFO receipt semantics only for an ordinary typed core without a promised core_tree. A present clock-model tree retains its explicit gate/info policy or defaults to gate; malformed models fail closed. Partition kits remain gated. Both Tcl measurement and Python consumer use the same selector. Numeric20ps tolerance, IO references, period/uncertainty, all measurement/coverage checks and actual TT/FF/pair policies are unchanged.

L2 parent gunit__t1 has an early tap u_gunit.u_l2.clk with old parent_budget276.7TT/226.9FF. A new closed view must publish its real measured means and update the matching provider/parent tap before parent consumption. This patch does not alter or qualify that parent contract. H0 eng__t1 currently has no early-core-tap declaration. No kit migration or route has been launched pending ROOT's scoped review.

Validation:47 targeted tests pass, including partition refusal, ordinary typed core, geometry-only slice, explicit/implicit model gates, malformed/empty models, broken typed IO reference, and existing G2 negative setup/hold/clock/coverage/reference tests. No RTL changed.
