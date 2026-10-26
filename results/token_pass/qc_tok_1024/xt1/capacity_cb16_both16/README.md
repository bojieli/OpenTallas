QC-TOK 10-24 13:4x: the capacity candidate plus CB16 tree-align pads, xt1 both clusters, lead 16, on intel2
(/srv/opentallas-scratch2/claude/qc-tok/xt1_cap_cb16_both16). The vehicle is Codex's xt1_capacity_both16_v2 with only the 7
qfd_qc_cb_* bound modules replaced, because the bound top and the carve are unchanged.
Bind: plan codex-qc-a0 (codex/qc-capacity-1024 @72ece79138), recipe ../../../../../physical/die_plan/qwen_compute/bind/
asbuilt_capacity_cb16.json = the capacity recipe + land_r8_extra qc_cb16_pads_capacity.json. That is 1,219,699 pads
(430,195 + 789,504), 78 types, 0 errors, 0 residual CB16 skew. verify PASS: 2,723,870 matched, 0 mismatched, lint 0.
xt1: nominal near 64/64 + far 64/64 PASS. The hr+1 mutant is numerically 64/64 + 64/64. The schedule gate is PASS
(the mutant is caught because the fixed consumer edges differ). The wrapper verdict on the mutant is preserved as numeric PASS.
Without the CB16 pads the same candidate FAILs 0/64 + 0/64 (../capacity_both16_v2).
Scope: RTL-functional carve smoke. This is not a generated-die token pass or physical signoff. The pad cost of CB16 alignment is an OWNER? item.
