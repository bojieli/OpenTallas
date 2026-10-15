qfd_tile_nl_banked_v1 (r13 NL helper, 2026-10-15): the node-less compute tile with the NK banked local clock-root
partition. 53 CLOSED data banks (NK's 58 minus face_n_b/face_n_y/node_stage_n_a/b/y; to_reg = qwen_glue_v514 holding the
TOREG edge that NK keeps inside the CLOSED node leaf), 11 V16 reset roots, 13 unchanged CLOSED children, 1 residual root.
Compiler edges: t_out age identical to NK banked (TOREG -> node_stage_t_out +1 -> face_t_out); ROM return +1, xdelay9,
TX198 shared unchanged with NK (same matvec source). No n_* ports.
Reference: qfd_tile_nl_staged_reference = original qfd_tile_nl + the same priced edges as NK's staged reference.
Verilator 5.032 on EPYC4 (/srv/opentallas-scratch/claude/q15-nl-banked-bench4, rerun after the to_reg mutant moved off a hard-child parameter override), real RTL + 10 real ROM via masks:
 m0 PASS 3499 full 514-bit words/264 outputs; allbanks PASS 5959/448, reads 64 120 96 104 64;
 FAULT (split 5 < SMIN 7 every third instruction) PASS 3499 (2712 fault words) and 5959 (5176);
 mutants TX m1/m2/m3 and to_reg bypass m4 all FAIL.
historical_unregistered_fault/: a first variant drove the tile fault into node_stage_t_out unregistered; the FAULT bench
rejected it (fault one cycle early, c887). NK banked's registered tf is correct: nk_fault_probe_run.log (NK banked vs
NK staged reference with the same split faults) PASS 3499.
Physical: kit physical/ref_tile/qfd_tile_nl_banked_v1 (held probe as NK, gate NOT launched). Physical qualification OPEN.
