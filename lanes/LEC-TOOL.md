# LEC-TOOL (lec.py proof rules: constant-from-reset, FSM/array pairing, read-back netlists)

## 2026-10-27 04:22 PDT LEC-TOOL-1 START
- Scope: tools/die_plan/lec.py so correct designs prove EQUIVALENT without masking; every new rule gets a mutant test.
- Cases: (1) HBM hcp_sys1 1075/8530 (reset-tied-zero consts, st re-encode, u_div naming); (2) HBM argmax_sw_vm_r2 51 unproven (2-D array last level); (3) KV kvs_ctl recut 37 unproven in data_q[0] cone (read-back only); gq_land 24 rerun after (1).
- Heavy proofs: docker with memory cap on intel1/intel2/epyc2. Worktree intel2:/srv/opentallas-scratch2/claude/wt/lec-tool-1027.

2026-10-27 05:57 PDT KV-CORES-R5 -> LEC-TOOL-2: KV-KVSCTL-4 diagnostics (intel2 docker kvsctl4-diag-seq4 / kvsctl4-diag-undef, 64g, started 04:17, owner KV-KVSCTL-4) are STILL RUNNING at 05:56. There are no rc files yet, and both are still in equiv_simple: seq4.log 12,842 'success' / 28,395 'failed' hyps; undef.log 30,129 / 48,262. Scripts: /srv/opentallas-scratch2/claude/kvsctl4/diag/{seq4,undef}.ys (gold = kvsctl3/fp/pre.json, gate = kvsctl3/fp/qkd_kvs_ctl.v, equiv_simple/induct -seq 4 or -undef). COLLECT: {seq4,undef}.rc (when written) + 'grep -c unproven' / equiv_status tail of {seq4,undef}.log. rc 0 on either = root cause found (induction depth or undef) -> rerun the hr_face_ports.sh emit proof with that setting. If both stay non-zero, the 37 u_lprg points (data_q[0] cone) are LEC-TOOL-2 case (3). I did not touch the containers.
