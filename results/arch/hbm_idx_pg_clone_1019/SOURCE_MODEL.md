# Exact clock-leaf PG omission and bounded source correction model

Scope: diagnostic clone of `hdie_col_idx256_1019-fan32g1-2727e1f68`; no shared helper change or adoption.

The frozen native `4_1_cts.log` records exactly 322 new clock buffers. `physical/common_flow/clk_net_protect.tcl::ot_protect_clock_tree`, installed by `ot_cts_fix_1_clk_net_protect.tcl`, marks those instances dont_touch immediately before CTS-stage repair_timing_helper. The frozen ORFS `final_report.tcl` invokes `final_connect.tcl`, whose only PG action is global_connect, before writing 6_final.odb. All 322 instances then produce ODB-0383, explicitly skipped in global connections. The final net-only PSM assertions report all supply shapes connected while omitting these 644 disconnected native terminals. No alternate clock source or net-label inference is needed to explain this failure.

Native stage receipts show missing PG pin counts 0 at PDN, 6528 after placement, 16962 after CTS, 17710 after GRT, 149914 after filler insertion/route, and exactly 644 after final global connections. Intermediate missing PG on newly added cells is therefore expected to persist until final binding in this frozen flow; those stage counts are not substituted for final qualification.

Proposed structural ordering, for independent ROOT-merger review:

1. Immediately before ot_protect_clock_tree marks a native instance dont_touch, inspect ALL its native MTerms with POWER/GROUND roles. Existing bindings must have the matching supply role and exact intended voltage-domain net. Bind only currently unbound terminals after resolving the actual declared supply mapping. Refuse unknown/ambiguous supply domains; do not derive voltage-domain identity from instance-name regex.
2. Check all protected native PG terminals after the operation, then apply the existing dont_touch protection unchanged. This adds no cell, edge, route or buffer delay. It changes physical connectivity metadata and therefore requires source/helper fingerprinting and an immutable gate rule classification.
3. After final global_connect, independently enumerate every native PG MTerm, including protected clock cells. Fail on missing/wrong-role terminals before the net-only PSM connectivity check. Intermediate insertion-stage missing counts remain diagnostics under the existing flow contract; they are not mandatory failure points. A PSM PASS is necessary but cannot replace final terminal coverage. Broader all-stage binding is outside this bounded model and would need a separate insertion-point inventory and coherent-flow proof.
4. Preserve existing full PG shape/contact connectivity checks, VDD/VSS short checks and layout legality. Binding a name is insufficient when legal conductor contact is absent. No blanket exemption or suppressed ODB warning is accepted.

The diagnostic clone temporarily clears dont_touch ONLY on each exact allowlisted clock instance, binds its two native supply pins to the existing matching supply nets, and restores its original protection. No resizer, CTS, placement, routing, timing or extraction command runs between those operations. This is a read-only-source diagnostic, not an authorized repair of the released route.

No production helper is edited in this packet. The earliest source-bound insertion/protection sequence and final skip are established; this does not claim every arbitrary future CTS hook is safe without the final native coverage guard.
