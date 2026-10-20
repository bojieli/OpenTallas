# Current retry pickup, 2026-10-20

The shared PG helper fix allowed h273b to complete: source f1361cdca, exact record 5318fd269, auto-merged main 19091fe54. Daemon verdict CLOSED: TT setup +300.80 ps, FF hold +29.27 ps, DRC 0; SS sensitivity +192.39 ps.

Own-R native audit of that exact exported record passes: launch 219.2 ps (pin b), capture 115.8 ps (dly[6]), TT/FF boundary spreads 2.1/1.7 ps, zero combinational pins. The launch margin to the 220 ps native budget is only 0.8 ps: die links still require actual compensated boundary timing. Input record hashes are committed alongside the receipt; extracted files are in /home/ubuntu/artifacts/codex-kv-ectl-pickup-1020/h273b_record. No original worktree or record modified.

ECTL lkp remains running on route attempt 3 (epyc9), reached final reporting after fill at 00:34. No duplicate launched. The old waived reset fanout of 369 remains an explicit blocker under the 23:45 binding census rule (maximum 32, resets included). A terminal CLOSED cannot silently waive that violation. Recompute base/FT lane permutations from its exact exported LEF when available, but do not treat geometric remapping as census qualification. KV-PARAMS3 owns the related structural K-tree/reset-base work.

The lkp retry completed and auto-merged: record 5f10ec86c, main ff56c6ba1, TT setup +198.95 ps / FF hold +23.07 ps / DRC 0, SS sensitivity **-88.42 ps**. The daemon CLOSED status therefore does not establish the owner SS headline clock requirement. Own-R native audit passes: launch153.2 ps, capture176.5 ps, TT/FF spread17.5/17.4 ps, zero combinational pins.

Lane placement was recomputed with the exact lkp exported LEF (SHA manifest), the existing lane8 reference LEF, RW=50 and ktree x=540. Base permutation: `2,1,5,4,7,0,6,3,9,8,13,10,11,15,14,12`, best worst hop409.8 um. Feed-through permutation: `2,1,5,4,7,0,6,3,9,8,11,10,13,15,14,12`, best worst hop417.9 um. Both need explicit reach treatment against405 um planning value. The derived script is the existing head_lane_perm.py with only its ktree LEF path changed; paths to the extracted reference are local artifacts.

Do not adopt solely on native PASS: the369-reset-load violation, negative SS sensitivity, and remaining hop reach obligations remain visible to the structural K-tree owner and die binder. No production binding changed.
