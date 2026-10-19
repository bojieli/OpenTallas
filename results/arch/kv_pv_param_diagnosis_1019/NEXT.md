# PV parameter diagnosis pickup

Branch `codex/kv-pv-param-diagnosis-1019`; packet `results/arch/kv_pv_param_diagnosis_1019`.

- Original positive, ordinary opt, width-opt each refuse176 cells; all source/view/reset-shell/parameter identities match. No production/helper change or receipt.
- Original911-comparison reset SAT12 base PASS; added916-comparison base PASS. Six actual reset-low edges, comparisons checked7..12, other inputs arbitrary. Diagnostic finite base only.
- Completed ep6 directory `/srv/opentallas-scratch/claude/kv-pv-param-diagnosis-1019/invariants`: unit347237/session30426, `equiv_invariants.log`: all916 PROVEN,0unproven. Adds exactly state[3]==0 and request nq[3:0]==0 as observations, no original comparison removed or assumptions added. Proof and base logs are in the packet; NOT PROVEN is refusal, not functional CEX. Root must review original-output/paired-state equivalence and actual valid-reset contract before any receipt.
- Live ep6 directory `/srv/opentallas-scratch/claude/kv-pv-param-diagnosis-1019/mut1`: unit1872662/session53219, `reset_bmc18.log`, `bmc18_cex.json` if failure. Previous same-MUT1 SAT12 was noncausal PASS: arrival check follows reset/start landing. Preserve it. Extract first actual differing observation and input/reset sequence only if real CEX exists.
- Existing causal-mutant collector unit1713334/session64834 ep6 `kv-params-1019` still finishing seq_xsM8. Five completed selected-causal predicates produce proof refusals with exact logs, no CEX claimed; copied in packet.
- Existing original PV join/slice/ASTK/seq/ktree native jobs and both GEN8 v2 lint chains are preserved. Do not duplicate/restart any progressing job. No strict qualification while any actual profile remains unqualified.

All jobs use remote copies, not this local worktree. Active jobs are recorded in pending_results and KV-PARAMS. No new native/helper adoption is authorized by this diagnostic packet.
