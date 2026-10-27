# LEC-TOOL (lec.py proof rules: constant-from-reset, FSM/array pairing, read-back netlists)

## 2026-10-27 04:22 PDT LEC-TOOL-1 START
- Scope: tools/die_plan/lec.py so correct designs prove EQUIVALENT without masking; every new rule gets a mutant test.
- Cases: (1) HBM hcp_sys1 1075/8530 (reset-tied-zero consts, st re-encode, u_div naming); (2) HBM argmax_sw_vm_r2 51 unproven (2-D array last level); (3) KV kvs_ctl recut 37 unproven in data_q[0] cone (read-back only); gq_land 24 rerun after (1).
- Heavy proofs: docker with memory cap on intel1/intel2/epyc2. Worktree intel2:/srv/opentallas-scratch2/claude/wt/lec-tool-1027.
