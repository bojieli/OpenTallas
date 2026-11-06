q3 link right-width store lock-step, main be7b72fcce1 (2026-11-05).
Source leaf copied from rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv; old/new differ only by module name and existing OT_HBM_RW_MACROS branch selection. Actual released behavioural SRAM models are copied byte-identically.
run.sh: Verilator5.050, 833ps clock, 12000 edges; directed full-address fill plus random write/read, current-address collision and previous-age bypass.
Result:11991 checked output words,0 mismatches; existing MUT1 single-bit output corruption detected on11991 words. PIN CYCLES0.
This proves the macro width/mask/no-repair change on the smallest affected vehicle. It does not claim routing or full kit LEC PASS.
