#!/usr/bin/env bash
# HARD-QC-FORMS-1: lock-step bench of the QC stm tload capture form (OT_QC_TLOADCAP).  Run from the repository root:
#   bash rtl/test/qwen_dv/tloadcap/run_tloadcap.sh OUTDIR
# Expect: base PASS (N=1), +N=0 FAIL, CAPTURE_MUT 1 FAIL, warm reset not moved FAIL; and both define forms of
# qfd_dv_s6_stm / qfd_dv_s6_stm_se0 elaborate (default = old parameters, OT_QC_TLOADCAP = CAPTURE_STAGE 1 / LOCAL_JOIN 1).
set -u; OUT=$1; mkdir -p "$OUT"; D=rtl/test/qwen_dv/tloadcap; SRC="rtl/qwen_dv/qfd_dv_slice_tload.sv rtl/qwen_dv/qfd_dv_table_rom_loader.sv"
rc=0
iverilog -g2012 -DSYNTHESIS -o "$OUT/tb" $D/tb_tloadcap.sv $SRC > "$OUT/build.log" 2>&1 || { echo BUILD FAIL; cat "$OUT/build.log"; exit 1; }
iverilog -g2012 -DSYNTHESIS -DTB_CAPTURE_MUT -o "$OUT/tb_mut" $D/tb_tloadcap.sv $SRC > "$OUT/build_mut.log" 2>&1 || { echo BUILD FAIL; exit 1; }
exp() { r=$(grep -o 'TLOADCAP_LOCKSTEP [A-Z]*' "$2" | head -1); echo "$1: ${r:-NO_RESULT} (expected $3)"; [ "$r" = "TLOADCAP_LOCKSTEP $3" ] || rc=1; }
vvp "$OUT/tb" > "$OUT/base.log" 2>&1;            exp "base N=1" "$OUT/base.log" PASS
vvp "$OUT/tb" +N=0 > "$OUT/n0.log" 2>&1;         exp "wrong N=0" "$OUT/n0.log" FAIL
vvp "$OUT/tb" +N=2 > "$OUT/n2.log" 2>&1;         exp "wrong N=2" "$OUT/n2.log" FAIL
vvp "$OUT/tb_mut" > "$OUT/mut1.log" 2>&1;        exp "CAPTURE_MUT 1" "$OUT/mut1.log" FAIL
vvp "$OUT/tb" +MUT=2 > "$OUT/mut2.log" 2>&1;     exp "warm reset not moved" "$OUT/mut2.log" FAIL
grep TLOADCAP_LOCKSTEP "$OUT/base.log"
echo "RUN_TLOADCAP rc=$rc"; exit $rc
