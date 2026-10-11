#!/bin/bash
# hgi-1010/g2 2026-10-10 (audit N9): the PS svc segments (SW) with the attention entry's REAL line-credit RTL as the
# consumer of all 8 row ports (ot_attn_ks_credit, the unit inside hfd_attn_half_lo, extracted from its source file),
# every stream credited.   run_bench_ps_entry.sh <out dir>   (from the source snapshot root)
#   sim_entry  legacy traffic + 12 per-PC streams, credits only from the entry RTL: PASS
#   neg_drop   OT_ATTN_MUT_KQ_DROP (every 16th credit lost): the credited streams stall -> must FAIL
#   neg_dup    OT_ATTN_MUT_KQ_DUP (every 16th credit doubled): must FAIL
set -u
O=$1; mkdir -p $O/ps; V=physical/hbm_accel_die_views/svc; T=$V/tb; rm -f $O/summary.txt
for f in $V/rtl/${SEGPS:-seg_ps}/*.sv; do
  sed -E 's/\b(hfd_svc_(SW|SE)_s[0-9]+)\b/\1_ps/g; s/\b(hfd_svc_(SW|SE|NW|NE)_seg)\b/\1_ps/g' $f > $O/ps/$(basename $f .sv)_ps.sv
done
awk '/^module ot_attn_ks_credit/,/^endmodule/' rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv > $O/ot_attn_ks_credit.sv
LIB="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/service/ot_hbm_kport_map.sv $V/rtl/ot_hbm_svc_core.sv $V/rtl/ot_hbm_svc_seg_lib.sv $V/rtl/ot_hbm_svc_ps_lib.sv rtl/common/ot_fwd_link_stage.sv $O/ot_attn_ks_credit.sv"
SF="$LIB $O/ps/hfd_svc_SW_s[0-9]_ps.sv $O/ps/hfd_svc_SW_seg_ps.sv $V/rtl/seg/hfd_svc_SW_s[0-9].sv $V/rtl/seg/hfd_svc_SW_seg.sv $T/tb_svc_physide.sv $T/tb_svc_ps_SW.sv"
sim() { local L=$1; shift
  iverilog -g2012 -DPS_STREAMS -DPS_ENTRY_CREDIT "$@" -o $O/$L.vvp -I $T -s tb_svc_ps_SW $SF > $O/build_$L.log 2>&1 || { echo "$L build FAIL" >> $O/summary.txt; return; }
  vvp -n $O/$L.vvp > $O/$L.log 2>&1; }
sim sim_entry & sim neg_drop -DOT_ATTN_MUT_KQ_DROP & sim neg_dup -DOT_ATTN_MUT_KQ_DUP & wait
rc=0
grep -q "^SVC_BENCH PASS" $O/sim_entry.log; r=$?; echo "sim_entry rc=$r $(grep SVC_BENCH $O/sim_entry.log | head -1)" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
for L in neg_drop neg_dup; do grep -q "^SVC_BENCH PASS" $O/$L.log && r=0 || r=1
  echo "$L rc=$r (must be nonzero) $(grep SVC_BENCH $O/$L.log | head -1)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1; done
echo "overall rc=$rc" >> $O/summary.txt; cat $O/summary.txt; exit $rc
