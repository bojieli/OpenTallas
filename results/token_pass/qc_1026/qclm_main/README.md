# QCLM: QC per-layer stage set on the bound s8 slice row, built fresh from main (TOK-QK, 2026-10-26)

Grade: RTL-functional, bound compute-die slice row, source assembly (Verilator 5.050). Not a die-netlist result, not whole-QC-top, not a whole-token / G5 claim.

## What ran
- Vehicle: tb_qfd_dv2 FACE 3 = the bound_r8 s8 slice row (qfd_dv_slice_die), DV2_S8DIE=1, defines OT_STATION_REGIONAL OT_S5_HARD OT_S6_SIM OT_S8_SIM OT_QFD_UP4_CK_ENTRIES OT_S8_CROM_ALIGN (CROM align 3, MIF 0).
- Source: git archive of main b272ba0ecbeb (raw/SOURCE_REVISION); 86 source files (raw/sources_main.f). No QC source or bench file in that list, rtl/test/qwen_dv or tools/qwen_tokfunc changed between b272ba0ec and main f57aae94a.
- Fresh build (raw/build.time: 55 min, 117 GB peak), slice + vec + MAT calibration with the main compiler, then tools/qwen_tokfunc/stage_stg_die.sh with the QCL r1 runlist (259 positive cases: per layer L0-L35 resid1 / resid2 / silu / qk with RoPE rx, qkv / gu / od with ARF, LM head, embedding, LGPOS).
- Run: epyc2 ot-run unit oth-ubuntu-3466220-1793040800, dir SCRATCH/tok-qk-qclm, script scripts/run.sh.

## Result
- QCLM_STG_DIE PASS, 259/259 positive cases matched, 0 problems (raw/result.json).
- Identity with QCL r1 (intel2 tok-qk-qcl/r1, the c1c42f554 binary whose preprocessed text differed from main): result.json, vec_ages.json, slice_ages.json and stn_ages.json are byte-identical (same sha256, raw/hashes vs raw/qcl_r1_hashes.txt). The preprocessed RTL differs by 693 diff lines (reset-pipe rewrite + MIF default-off), and that difference does not change any case verdict, span or measured age.
- So the per-layer QC compute stage set now holds on current main.
- Per-case spans (core cycles, 833 ps): resid 1173, silu 945, qk 1192, qkv delivery 445, gu delivery 437, od 1555 span. Ages: raw/vec_ages.json, for example add_psum_out 174/190/206, red_vm 174, silu_out 199/207, d2d rs 127.

## Not covered
- The whole-QC top on the ONEQC final landing bind (that bind is not final).
- The head / attnret / xhead stages on this row: attnret is run separately; the head leaf is byte-identical to the 10-24 run; xhead only exists on slice2.
- KV-side stages.
