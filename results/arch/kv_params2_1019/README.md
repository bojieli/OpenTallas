# KV-PARAMS2 (K.STA.PARAMS) native parameter receipts -- joint mode

Tool: tools/qwen_kv_die/kv_param_native_audit.py (this branch): --observe-zero-regex, --observe-ge, --macro-model, --reset-base.
Fixture tests: tests_joint_mode.log (7/7 OK, fleet).

## Root cause of the 213 u_cc base mismatches (Codex 2c2bd3c92)
The Codex joint_base left gold (RTL) and gate (routed netlist) power-up states independent. Both hold the same
unreset 7-deep datapath (kp_r -> ca -> s1 -> cb -> cd -> s2 -> cc); two independent power-up words of the SAME register
disagree until flushed (7 edges > 6 reset edges). RTL-vs-RTL fails identically (base_diagnosis/selftest.*: independent
FAIL, paired SUCCESS). Not a source/native difference. A first paired base (v1) still failed: decode
(ktree_paired_base_v1_decode.txt) shows the step-1 free *_err[1] metadata registers (gold-only, tied 0 in the netlist)
corrupting s1_small/... at step 2 and reaching 23 g_n[7] u_cc bits at step 7. Final base: one power-up state --
every paired non-replica register equal at step 1, metadata registers with no routed flop take the netlist's tied 0,
replicas / other gold-only registers / range predicates free; every original comparison + observation is a miter
output at steps 7..10 after 6 reset-low edges. No comparison removed, no reset extension.

## Status
- ot_qwen_tp8_pv_wide_ctl_tb: PROVEN 916/916 + base (6 edges, 688 paired); MUT1 control NOT PROVEN 877/916. Receipt in receipts/.
- ktree, lane8, pv_join_t, seq_xs_s (+MUT8), pv_slice_t (+RESET_PIN0): fresh joint audits LIVE on ep6
  /srv/opentallas-scratch/claude/kv-params2-1019/audits (see pending_results).
- 10 modules already PROVEN by Codex audits (results/arch/kv_gen8_pickup_1019/audits on codex/native-profile-contract-1019).
Receipts must be re-issued with `kv_param_native_audit.py receipt --root <GEN9 source tree> --audits <dir>`: the
receipt checks the view/RTL/source identity against that tree.
