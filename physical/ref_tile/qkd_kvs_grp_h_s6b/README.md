# qkd_kvs_grp_h_s6b (KV-GRP6 10-20, K.STA.GRP)

Top qkd_kvs_grp_h_s6c = bounded-driver structural copy (tools/qwen_kv_die/kv_grp_safe5.py, Codex generator) of the ORFS-mapped s6 RTL
(rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s6.sv, tools/qwen_kv_die/kv_grp_safe6.py): the 1024-b response payload
delay is a genuine SRAM ring per PC branch (8 x ot_sram_1r1w_4x32_m1_p192_grp_rsp: write wp at e1, read previous slot at
e2, kept exit copies at e3), +0 cycles.  Generator input/metadata: results/rtl/qwen_kv_die/kvs_grp_s6_1020/{inputs,qkd_kvs_grp_h_s6c.json}.

SAFE checklist (pre-gate):
1 Pins: every face registered in source (s2/s3 faces, two kept exit copies on rsp/krsp); 2-stage reset landing in source. PASS
2 Reach: planned out_data->ring <= ~330 um, ring->exit <= ~375 um (ring stacks between PC read faces and the E exits). PASS (plan; gate GRT checks)
3 Fanout: generator max 32 terminal loads per driver (resets included); authoritative number = this gate's pre-floorplan native_census.json. PASS (generator)
4 Depth: unchanged s3 logic; ring adds one AND (reset-zero) before the macro write. PASS
5 Storage: payload delay in 32 SRAM macros (4096 b) instead of 2 x 1024 flop stages; rows 4 x 32 kb SRAM; boot FIFOs 1168 b each (< 2 kb). FIXED (s6)
6 Floorplan: 388.8 square, 4 row macros on the 43.2 lattice (unchanged), 4 abutted 8-macro ring stacks (pitch 14.352, MY) at x 163.2 / 335.52, y 22.176 / 157.008; >= 20 um channels; upper band y > 278 full width. PASS (ref_tile gen, no channel/offtrack finding)
7 Clock: spine ck+hck, variant a pad 0 / b pad 1; ring macros are spine macro leaves; pin-flop spread <= 80 TT+FF checked at the gate. PENDING gate
8 Schedule: static, +0 cycles (bench-proven ages vs the sha-pinned S2REF). PASS
Benches: RTL kvs_grp_safe6_bench.py m0 PASS 292950 (seeds 1020/1/77/31337) + mutants m6 m9..m14 FAIL (results/.../b1); structural kvs_grp_safe6c_bench.py m0/m1/m2 (results/.../b2).
Ring mask/enables are constant by construction (write+read every edge), as the row macros' mask; not a functional tie.
