qfd_tile_nk_banked_v2 (PM-H-S interleaved W faces), Q-COMPUTE-ELEM r13 2026-10-15. Generator
physical/qwen_tile_glue_banks_1015/make_parent_v2_interleave.py; RTL rtl/qwen_sys/tile_parent_banked_20261015/qfd_tile_nk_banked_v2.sv
(4 W face qwen_glue_v514 -> 2 qwen_glue_x1028; same registers/clocks/resets; zero added edges).
Verilator on EPYC4 (ot-run oth-ubuntu-2865199), real RTL + 10 real ROM via masks (prepare_parent_bench_v2.py):
 m0 tb_parent_banked          PASS checks3499 output264 node438  (identical to v1)
 allb tb_parent_banked_allbanks PASS checks5959 output448 node745
 boot tb_parent_banked_boot16 PASS checks3559 output264 node445
 face OT_FACE_MUT (n_b capture rotated 1 bit)  FAIL c101 node complete word  (expected)
 m1 TX mutant                 FAIL c134 tile complete word (expected)
Physical: kit generator make_parent_v2_kit.py waits for the CLOSED qwen_glue_x1028 view.
