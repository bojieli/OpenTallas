#!/usr/bin/env bash
# HBM-CORES-B 11-12 RCMD unit bench: the repo async-FIFO bench (tb_hbm_svc_async_fifo, back-to-back pops, both clock
# ratios, depth 4/8, async flushes) on ot_hbm_svc_async_fifo_re.  gate must PASS every config; MUT=1 (unsafe late empty) must FAIL at least one config
# (it needs a pop right after the last entry, which the bench ready pattern hits only in some clock ratios).
# Run from the repo root: bash physical/die_plan/hbm_arch_cores/proofs/ksh_rcmd_1112/run_fifo_re_bench.sh OUTDIR
set -uo pipefail
out=${1:?output directory}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
awk "/^module ot_hbm_svc_async_fifo_re #/{p=1} p{print} p&&/^endmodule/{exit}" $d/ot_hbm_svc_vm_kshare_splitstrap.sv > "$out/fifo_re.sv"
git show HEAD:rtl/lib/ot_reset_sync.sv > "$out/ot_reset_sync.sv" 2>/dev/null || cp rtl/lib/ot_reset_sync.sv "$out/"
git show HEAD:$d/tb_hbm_svc_async_fifo.sv 2>/dev/null > "$out/tb.sv" || cp $d/tb_hbm_svc_async_fifo.sv "$out/tb.sv"
sed -i "s/^ parameter integer DEPTH=8;/ parameter integer DEPTH=8,MUT=0;/; s/ot_hbm_svc_async_fifo #(.WIDTH(284),.DEPTH(DEPTH)) dut/ot_hbm_svc_async_fifo_re #(.WIDTH(284),.DEPTH(DEPTH),.MUT(MUT)) dut/" "$out/tb.sv"
grep -q "ot_hbm_svc_async_fifo_re #" "$out/tb.sv" || { echo "tb patch failed"; exit 2; }
rc=0; mfail=0
for mut in 0 1; do for depth in 4 8; do for dir in 0 1; do
 if ((dir==0));then wh=512;rh=416.666667;else wh=416.666667;rh=512;fi
 n=m${mut}_d${depth}_${dir}
 iverilog -g2012 -s tb_hbm_svc_async_fifo -Ptb_hbm_svc_async_fifo.DEPTH=$depth -Ptb_hbm_svc_async_fifo.MUT=$mut -Ptb_hbm_svc_async_fifo.WR_HALF=$wh -Ptb_hbm_svc_async_fifo.RD_HALF=$rh -o "$out/$n.vvp" "$out/ot_reset_sync.sv" "$out/fifo_re.sv" "$out/tb.sv" || { echo "BUILD_FAIL $n"; rc=2; continue; }
 vvp "$out/$n.vvp" > "$out/$n.log" 2>&1
 if grep -q "PASS HBM_FIFO" "$out/$n.log"; then got=PASS; else got=FAIL; fi
 exp=PASS; ((mut==1)) && exp=FAIL
 echo "CASE $n expect $exp got $got :: $(grep -m1 -E "PASS HBM_FIFO|FATAL|mismatch|fault" "$out/$n.log")"
 ((mut==0)) && [ $got != PASS ] && rc=1
 ((mut==1)) && [ $got = FAIL ] && mfail=$((mfail+1))
done; done; done
echo "SUMMARY gate all-pass=$([ $rc = 0 ] && echo yes || echo no) mutant1 rejected in ${mfail}/4 configs"
[ $mfail -ge 1 ] || rc=1
exit $rc
