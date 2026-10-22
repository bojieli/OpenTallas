# qkd_kvs_emb_x2a — KV-EMB6 10-20 (parent kvs_emb CTX, native32 components ON, child c1b STAND-IN)
e2a/x1 fanout classification: v3/hot[0..2] (join4 one-hot payload select, qkd_embedding_static_join4.sv l.26-28) 298 loads = FUNCTIONAL
critical-cone driver (not reset, not benign); x1 mapped census 30 drivers >32 (29 functional), reset 316, max 593 -> FAIL, not waivable.
Structural fix = Codex f0113c9c6 NATIVE32+PIPE_JOIN (registered local select groups join_fan32, per-segment counter copies, banked ctx,
ot_rst_relay regional reset); per-component loaded-Lib census PASS32 (cal 8657 roots, ctx 864). This kit census = whole parent (gate mandatory).
1 Pins: inherited parent face wrapper (pin regs per spec). 2 Reach: 388.8x302.4 parent, gate measures. 3 Fanout: components PASS32; whole-parent gate census.
4 Depth: gate measures. 5 Storage: row SRAM in child; calendar 192 b + ctx state < 2 kb. 6 Floorplan: child MY@(86.4,86.4) lattice slot (Codex plan).
7 Clock: OT_SPINE_SYM spine (x1a recipe, 39.6/35.7 on c1b). 8 Schedule: +2 active (CTX1+join1), +6 parallel reset release -> KV-GEN9 INBOX.
STAND-IN: child = CLOSED c1b view (its own native FAIL 1082) until n32b/n32c closes; NOT submittable. Benches in job.json are the legacy
default-param lockstep bench; a NATIVE32=1 lockstep bench + witnesses are owed before submit.
