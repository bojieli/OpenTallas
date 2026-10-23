#!/usr/bin/env bash
# hier_wrap_equiv.sh <name> <slice dir (boundary.json slice.v masters.txt)> <bundle-like dir with views.json/rtl/flatten_masters.py> [FAULT_SED]
# Builds the slice twice under the bench's hierarchical recipe: plain (flat top) and HIERWRAP; runs the random trace tb; compares.
set -u
N=$1; SL=$(readlink -f $2); BB=$(readlink -f $3); FAULT=${4:-}
G=$(cd "$(dirname "$0")" && pwd); V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=${EQ_ROOT:-$PWD}/eq_$N; rm -rf $D; mkdir -p $D; cd $D
for f in $(ls $BB); do case $f in masters|slice|obj*|masters_*) ;; *) ln -s $(readlink -f $BB/$f) $f;; esac; done
mkdir slice; cp $SL/slice.v $SL/masters.txt $SL/boundary.json slice/
python3 $G/equiv_trace_tb.py --slice slice
python3 flatten_masters.py --bundle . --views views.json --hier 1 --nohier "" --verilator $V > flatten.log 2>&1 || { tail -3 flatten.log; exit 3; }
[ -n "$FAULT" ] && { eval "$FAULT"; echo "FAULT applied: $FAULT"; }
cp -r masters masters_orig
b() { sed 's#^#masters/#; s#$#.sv#' slice/masters.txt > slice/masters.f; S=slice/slice.v
  if [ $1 = hw ]; then rm -rf masters; cp -r masters_orig masters; python3 $G/hier_param_wrap.py --bundle .; echo slice/hier_wraps.sv >> slice/masters.f; S=slice/slice_hw.v; fi
  /usr/bin/time -v -o time_$1 bash -c "$V --cc --exe --main --timing --hierarchical -j 1 -O1 --unroll-count 16384 --unroll-stmts 4000000 --top-module tb_hbm_slice -Mdir obj_$1 -Wno-fatal -Wno-lint -Wno-style -Wno-MODDUP -Wno-PINMISSING -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD -Wno-INITIALDLY -Wno-COMBDLY -Wno-BLKANDNBLK -Wno-SELRANGE -Wno-WIDTH -Wno-CASEINCOMPLETE --x-initial unique --x-assign unique -f slice/masters.f $S slice/tb_slice.sv && make -C obj_$1 -f Vtb_hbm_slice_hier.mk -j1 hier_verilation && make -C obj_$1 -f Vtb_hbm_slice_hier.mk -j 16 hier_build" > build_$1.log 2>&1 || { echo "BUILD_FAIL $1"; grep -m3 %Error build_$1.log; return 1; }
  ./obj_$1/Vtb_hbm_slice +verilator+rand+reset+0 > run_$1.log 2>&1
  echo "$1 peakGB=$(awk '/Maximum resident/{printf "%.1f", $6/1e6}' time_$1) top_cpp_MB=$(du -cm obj_$1/Vtb_hbm_slice___024root*.cpp | tail -1 | cut -f1) protectlib_calls=$(cat obj_$1/Vtb_hbm_slice___024root*.cpp | grep -c protectlib) $(grep TRACE_FINAL run_$1.log)"; }
b flat; b hw
if diff <(grep TRACE_ run_flat.log) <(grep TRACE_ run_hw.log) >/dev/null; then echo "EQUIV PASS $N ($(grep -c TRACE_ run_flat.log) checkpoints bit-exact)"; else echo "EQUIV FAIL $N"; diff <(grep TRACE_ run_flat.log) <(grep TRACE_ run_hw.log) | head -4; fi
