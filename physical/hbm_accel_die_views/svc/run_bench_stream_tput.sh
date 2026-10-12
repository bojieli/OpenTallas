#!/bin/bash
# tput-map-1011/F1: SVC.STREAM production-shape throughput bench (tb/tb_svc_ps_stream_tput.sv) under Verilator.
#   run_bench_stream_tput.sh <out dir> [fam SW|NE] [segdir seg_psfc|seg_ps] [mut]
# Builds one binary per (fam, segdir, mut) and runs the phase / credit sweep; summary in <out>/summary.txt.
# mut=slot: the PS sector slot ignores the row's bank XOR (run_bench_ps.sh neg_slot) -> must FAIL.
# mut=rob: the per-PC reorder buffer drains without waiting for the sector (tputx-svc) -> must FAIL.
# (run from the source snapshot root)
set -u
O=$1; FAM=${2:-SW}; SD=${3:-seg_psfc}; MUT=${4:-}
V=physical/hbm_accel_die_views/svc; T=$V/tb
mkdir -p $O
LIB="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/service/ot_hbm_kport_map.sv $V/rtl/ot_hbm_svc_core.sv $V/rtl/ot_hbm_svc_seg_lib.sv"
PSLIB=$V/rtl/ot_hbm_svc_ps_lib.sv
if [ "$MUT" = slot ]; then
  sed 's/wire \[1:0\] slot = bb_r\[1:0\] ^ rr\[1:0\];/wire [1:0] slot = bb_r[1:0];/' $PSLIB > $O/ps_mut_slot.sv
  cmp -s $O/ps_mut_slot.sv $PSLIB && { echo "slot mutant not applied" >> $O/summary.txt; exit 2; }
  PSLIB=$O/ps_mut_slot.sv
fi
if [ "$MUT" = rob ]; then   # tputx-svc: the ROB drains a sector without waiting for it to land -> must FAIL under reorder
  sed 's/wire dr = dact \&\& rvh \&\& /wire dr = dact \&\& /' $PSLIB > $O/ps_mut_rob.sv
  cmp -s $O/ps_mut_rob.sv $PSLIB && { echo "rob mutant not applied" >> $O/summary.txt; exit 2; }
  PSLIB=$O/ps_mut_rob.sv
fi
if [ $FAM = NE ]; then SEGS="$V/rtl/$SD/hfd_svc_SE_s[0-9].sv $V/rtl/$SD/hfd_svc_NE_seg.sv"; DEF=-DFAM_NE
else SEGS="$V/rtl/$SD/hfd_svc_SW_s[0-9].sv $V/rtl/$SD/hfd_svc_SW_seg.sv"; DEF=; fi
RW=${RW:-16}; DEF="$DEF -DOT_TPUT_RW=$RW"
L=${FAM}_${SD}_rw${RW}${MUT:+_mut$MUT}
verilator --binary --timing -j 16 -O2 -Wno-fatal -Wno-lint -Wno-style $DEF --top-module tb_svc_ps_stream_tput -I$T \
  --Mdir $O/vlt_$L $LIB $PSLIB $SEGS rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv $T/tb_svc_physide.sv $T/tb_svc_ps_stream_tput.sv \
  > $O/build_$L.log 2>&1 || { echo "$L build FAIL" >> $O/summary.txt; tail -20 $O/build_$L.log; exit 3; }
if [ -n "$MUT" ]; then RUNS="0:0"; else RUNS=${RUNS:-"0:0 1300:0 2700:0 4100:0 5500:0 0:1 2700:1"}; fi
for r in $RUNS; do
  ph=${r%:*}; cr=${r#*:}
  ( $O/vlt_$L/Vtb_svc_ps_stream_tput +nsec=${NSEC:-4092} +nstr=${NSTR:-2} +phase_ns=$ph +cred=$cr > $O/run_${L}_p${ph}_c${cr}.log 2>&1
    echo "$L p$ph c$cr $(grep -h '^SVCTPUT ' $O/run_${L}_p${ph}_c${cr}.log | head -1) $(grep -h 'SVCTPUT_BENCH' $O/run_${L}_p${ph}_c${cr}.log)" >> $O/summary.txt ) &
done
wait
