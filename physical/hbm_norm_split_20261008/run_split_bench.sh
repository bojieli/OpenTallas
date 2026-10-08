#!/bin/bash
# run_split_bench.sh <outdir> <8|16> [mut]   (cwd = repo root): transaction-level exactness of the partitioned norm
# engine (ot_hbm_norm_split_view_g<G>) against the flat MEM1 view (ot_hbm_norm_engine_view), tb_hbm_norm_split on the
# DS1M golden row + 3 overlapped rows + gain reload.  Both DUTs must PASS their own golden-row check, and the split's
# y / q / rstd stream must equal the reference's byte for byte.  mut: +define+OT_NSPLIT_MUT (group 1's tree partial
# replaced by group 0's) -- the negative control must print FAIL at line start.
set -u; O=$1; G=$2; M=${3:-}; mkdir -p $O
V=physical/hbm_norm_split_20261008; G0=results/rtl/hbm_norm_engine_view_20261006/gold
MACV=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
srcs="$(cat $V/sources.f | tr '\n' ' ') physical/hbm_norm_engine_view_mem1_20261007/ot_hbm_norm_engine_view.sv $MACV rtl/test/tb_hbm_norm_split.sv"
build() {  # build <dir> <defines>
  verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $2 --top-module tb_hbm_norm_split -Mdir $1/obj $srcs \
    --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $1/build.log 2>&1
}
DEF="+define+OT_NSPLIT_G$G"; [ "$M" = mut ] && DEF="$DEF +define+OT_NSPLIT_MUT"
mkdir -p $O/ref $O/dut
build $O/ref "" & p1=$!
build $O/dut "$DEF" & p2=$!
wait $p1 || { echo "BUILD_FAILED ref"; tail -n 5 $O/ref/build.log; exit 3; }
wait $p2 || { echo "BUILD_FAILED dut"; tail -n 5 $O/dut/build.log; exit 3; }
for d in ref dut; do mkdir -p $O/$d/run; cp $G0/*.mem $O/$d/run/; (cd $O/$d/run && ../obj/Vtb_hbm_norm_split > ../run.log 2>&1) & done; wait
grep -h "^SPLITBENCH" $O/ref/run.log | sed 's/^/ref /'; grep -h "^SPLITBENCH" $O/dut/run.log | sed "s/^/g$G /"
rp=$(grep -c '^PASS' $O/ref/run.log); dp=$(grep -c '^PASS' $O/dut/run.log)
# per-kind streams in order (y, q and rstd interleave differently: q is one cycle later relative to y in the split)
nl=$(wc -l < $O/ref/run/stream.txt); same=0
for t in Y Q R F; do grep "^$t " $O/ref/run/stream.txt > $O/ref_$t.txt; grep "^$t " $O/dut/run/stream.txt > $O/dut_$t.txt
  cmp -s $O/ref_$t.txt $O/dut_$t.txt || { same=1; echo "STREAM $t differs: $(diff $O/ref_$t.txt $O/dut_$t.txt | grep -c '^<') lines"; }; done
echo "STREAM lines=$nl identical=$([ $same = 0 ] && echo yes || echo no) ref_pass=$rp dut_pass=$dp"
if [ "$rp" = 1 ] && [ "$dp" = 1 ] && [ $same = 0 ] && [ "$nl" -gt 600 ]; then echo "PASS split_g$G"; exit 0; fi
echo "FAIL split_g$G"; exit 1
