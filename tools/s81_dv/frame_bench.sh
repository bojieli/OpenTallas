#!/bin/bash
# frame_bench.sh <outdir> [MASTER=col_h9] [MUT=0|xlane|marker|tree|cfgbank] (cwd = repo root): the exact S81-DV frame bench
# (tools/s81_dv/frame_bench.py; tb rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame.sv).  MUT 0 = the emitted wrapper
# (rtl/dsrom_sys/s81_dv/frame/<MASTER>.sv) must PASS; a mutant re-emits the wrapper with one wiring fault into <outdir>
# (tools/s81_dv/frame_wrap.py emit --mutant) and must FAIL.  Exit 0 = the expected verdict.
# One build; vector sets (SET):
#   each (default)  one run per q element k of the frame (gen --only k): that element alone holds MATS (4) one-row
#                   K-1024 matrices (4 super rows, macro b idle: no same-edge r0 / r1 leaf pair), so
#                   every q element's x / cfg / ROM / leaf path and its return path to the root is exercised exactly
#   all             one run, all 12 q elements share one phase (ROWS 8, K-split): see the lane notes (static return
#                   tree F1 at the element r0 / r1 leaf pair) -- diagnostic, not part of the verdict
# Env: SEED (1), ROWS, MATS, KK, CYC (3000), J (build jobs, 8), VFLAGS (extra verilator flags).
set -u
O=$1; MASTER=${2:-col_h9}; MUT=${3:-0}; SET=${SET:-each}
mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
FL=tools/s81_dv/frame_bench.f
if [ "$MUT" = 0 ]; then FR=rtl/dsrom_sys/s81_dv/frame; else
  python3 tools/s81_dv/frame_wrap.py emit --mutant $MUT --out-rtl $(realpath $O)/rtl > $O/mutant.log 2>&1 || { echo "MUTANT_EMIT_FAILED"; tail -3 $O/mutant.log; exit 3; }
  FR=$(realpath $O)/rtl; fi
if [ ! -x $O/obj/Vtb_s81dv_frame ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
    -Wno-MULTIDRIVEN ${VFLAGS:-} -DFRAME=$MASTER -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 --top-module tb_s81dv_frame -Mdir $O/obj \
    -f $FL $FR/$MASTER.sv rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame.sv \
    --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
    || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
fi
if [ "$SET" = all ]; then KS="all"; else
  KS=$(python3 -c "import sys; sys.path.insert(0, 'tools/s81_dv'); import frame_bench as B; print(' '.join(map(str, B.frame_pairs('$MASTER')[0])))"); fi
npass=0; nfail=0
for k in $KS; do
  VD=$O/vec_$k
  if [ "$k" = all ]; then A="--rows ${ROWS:-8} --mats ${MATS:-1} --K ${KK:-2048}"; else A="--rows ${ROWS:-1} --mats ${MATS:-4} --K ${KK:-1024} --only $k"; fi
  [ -f $VD/meta.json ] || python3 tools/s81_dv/frame_bench.py gen --master $MASTER --out $VD --seed ${SEED:-1} $A \
     --cycles ${CYC:-3000} > $O/gen_$k.log 2>&1 || { echo "BENCH_SETUP_FAILED gen $k"; tail -3 $O/gen_$k.log; exit 4; }
  $O/obj/Vtb_s81dv_frame $(cat $VD/ARGS) > $O/run_$k.log 2>&1
  if python3 tools/s81_dv/frame_bench.py check --dir $VD --log $O/run_$k.log > $O/check_$k.log 2>&1; then npass=$((npass+1))
  else nfail=$((nfail+1)); fi
  echo "  [$k] $(tail -n 1 $O/check_$k.log)"
done
echo "FRAME_SET $MASTER MUT=$MUT set=$SET pass=$npass fail=$nfail"
if [ "$MUT" = 0 ]; then [ $nfail = 0 ] && [ $npass -gt 0 ] && { echo "PASS frame $MASTER"; exit 0; }; echo "FAIL frame $MASTER"; exit 1; fi
[ $nfail -gt 0 ] && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$MUT $MASTER"; exit 0; }
echo "NEGATIVE_CONTROL_PASSED MUT=$MUT $MASTER (bench blind)"; exit 1
