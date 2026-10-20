# HBM-H9BIND 10-20: GEN2e4 die binds the CLOSED h9c PC controller (MC3c deferred to next release)
See PACKET.json (bind manifest, SHAs, ABI/calendar/old-rate scope). Evidence on ep6 /srv/opentallas-scratch/claude/codex-hbm-die11-1020
(fallback_unread/{review_h9bind.json,manifest_proposal_h9bind.json,replay_h9bind/}, h9bind_bench/out, h9bind_snap.git).
- run_fallback_strict_h9bind.sh: Codex run_fallback_strict.sh + GIT_DIR historical-source lookup fix + renewed review inputs.
- make_review_h9bind.py: renewed delta review (4 a6572c814 re-pins, 0 entry changes). Digest admission by LEAD owed.
- run_h9b_abi_benches.sh: H9B_TXN pass + RMUT1 fail witness, PC_REFCFG pass + 4 mutants (iverilog, ep6).
Result: STRICT PASS unread 0 / tied 0 / structural 0 (strict_replay.log).
