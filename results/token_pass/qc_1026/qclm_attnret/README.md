# QCLM-ATTNRET: attention-return family on the bound s8 slice row (TOK-QK, 2026-10-26)

Grade: RTL-functional, bound compute-die slice row, source assembly. This is the same build and source as qclm_main.

## What ran
- Bench: dv_lower_vec_bench.py --mode attn on the QCLM obj_n12 (main b272ba0ec, tb_qfd_dv2 FACE 3, DV2_S8DIE=1, CROM align 3), using QCLM's measured vec_ages.
- Protocol: tools/qwen_tokfunc/stage_attnret.sh. The bound row has the pos config only.
- Run: epyc2 ot-run unit oth-ubuntu-478165-1793050116.

## Result
- PASS. Nominal: measured span 149 edges = compiled 149, owners [0,1,3,5]. The ddwin and ddbase mutants FAIL, as required.

## Delta
- On the predecessor slice2 (10-24, r1024) the span was 98, owners [0,1,2,5]. The composer's fallback is 137 (the compiled value).
- So the bound row's attention return is +51 vs slice2 and +12 vs the composer fallback.
- The effect on the token price of a +12 to +51 per-layer attention-return term has not been composed (UNCHECKED). Run the next compose on the current dies with this record.
