# Release token validation, 2026-10-19

Scope: recover idle fleet results and advance the smallest useful source-pinned simulation. No release target has a full native SU/MU token proof in this record. Existing die and token builds are preserved.

HBM `hbm_results.json` summarizes eleven completed component probes from the preserved sw5e and swx2b binaries; each has source-hash acceptance, raw log and runtime. Verilator process exit zero only means the bench finished. Every positive replay fails its explicit acceptance, so no token timing is promoted. DS L0 first fails SU record23 at serial2727 on both binaries; DS L2/L14 also fail. Qwen rank0/rank5 L0 p0 each commit1152 of1200 checks, first failure record6 at serial3209; p1 fails all224 checks. Later-chain jobs remain live and are not duplicated.

A 3700-stream-cycle DS L0 `+SHOWVAL` probe uses the same binary and replay under the fleet admission guard, with hashes of binary, bench and replay. Its purpose is to identify actual versus expected VM data at the first failure before changing RTL or loader schedules. It is intentionally an incomplete diagnostic. Pickup is in coordinator pending_results, lane RELEASE-TOKEN-CODEX.

The S81 m2 canonical MU result is in `../xdie_s81_1019/record.json`; it proves link delivery and bounded landing timing for three tagged users, not a full token or all46 users. Inherited source and prior failure witnesses come from claude/xdie-s81-2-1019@985b7fc9f. The two user-latency-equality predicates remain false and visible.

Release next steps: source-pinned representative layers including head/draft, exact producer/consumer and initial-state provenance, SU/MU calendar and co-sim on release GEN, then final token evidence. HBM MU/MTP remains next-release study.
