Native TX feed-forward stage source refinement (2026-11-06)

Target: canonical native ot_s81_kp4_enc_la LA2 FF1 stream equals LA2
FF0 stream delayed exactly one clock edge; fault output remains same edge.
Native ot_s81_kp4_enc remains old golden; unchanged tb_kp4_enc_la tests LA1
cycle-for-cycle and LA2 delayed exactly one edge. Full 544-bit words and
valid are compared. Continuous flow has no drops/duplicates; stall raises
sticky fault identically. Midstream reset flushes both control paths;
comparison resumes after synchronous leaf reset release. Native PMA
wrapper test compares the entire pma_tx output including finite PMA LAT4.
PMA data flops have no reset; their finite reset/drain interval is excluded.

Mutants: MUT1 inverts parity symbol7, MUT2 flips fq[0][0] partial,
MUT3 omits added parity-load edge. These are rejected by the same full-word
bench; expected nonzero exit is explicitly required by run_ff_proof.sh.

Exact compiled inputs are under inputs; SHA256 manifest binds the tested
snapshot. Tested encoder9aacfcbe differs from candidate44f04f55 only in
comments/whitespace and removal of unused genvars h,o; token_equivalence.json
records normalized exact equality. Candidate source commit is frozen by
parent. No physical or timing qualification is implied by this RTL proof.

EP5 run root: /srv/opentallas-scratch2/claude/codex-hbm-tx-feed-proof
Actual dedicated filesystem device2305; root device2304. Ordinary ot-run
admission, no floor overrides. Initial8GB client admitted while cancellation
raced; it completed nativeLA1 but then lost stdout at grep. That result is
preserved. Its replacement4GB duplicate remained unstarted and was cancelled.
Ordinary4GB resume retained nativeLA1, ran all other cases, and records its
actual maxRSS through /usr/bin/time -v. Logs and exact summary record per-case completion.
