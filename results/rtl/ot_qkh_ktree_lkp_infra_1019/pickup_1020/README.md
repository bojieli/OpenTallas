# Current retry pickup, 2026-10-20

The shared PG helper fix allowed h273b to complete: source f1361cdca, exact record 5318fd269, auto-merged main 19091fe54. Daemon verdict CLOSED: TT setup +300.80 ps, FF hold +29.27 ps, DRC 0; SS sensitivity +192.39 ps.

Own-R native audit of that exact exported record passes: launch 219.2 ps (pin b), capture 115.8 ps (dly[6]), TT/FF boundary spreads 2.1/1.7 ps, zero combinational pins. The launch margin to the 220 ps native budget is only 0.8 ps: die links still require actual compensated boundary timing. Input record hashes are committed alongside the receipt; extracted files are in /home/ubuntu/artifacts/codex-kv-ectl-pickup-1020/h273b_record. No original worktree or record modified.

ECTL lkp remains running on route attempt 3 (epyc9), reached final reporting after fill at 00:34. No duplicate launched. The old waived reset fanout of 369 remains an explicit blocker under the 23:45 binding census rule (maximum 32, resets included). A terminal CLOSED cannot silently waive that violation. Recompute base/FT lane permutations from its exact exported LEF when available, but do not treat geometric remapping as census qualification. KV-PARAMS3 owns the related structural K-tree/reset-base work.
