#!/usr/bin/env bash
# HBMc/TOKEN2 (10-22): flat Verilator 5.050 build + run of a collar_path_bench.py output.
#   BUNDLE=<make_bundle root (rtl/ physical/ views.json flatten_masters.py)>  DIR=<collar_path_bench --out>  [JOBS=8]
# Builds in DIR/b (symlinked bundle + DIR/slice, flat masters: the bench samples nets inside collar instances).
set -u
BUNDLE=$(readlink -f ${BUNDLE:?}); DIR=$(readlink -f ${DIR:?}); JOBS=${JOBS:-8}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
B=$DIR/b; mkdir -p $B; cd $B
for f in $(ls $BUNDLE); do case $f in slice|masters|obj*) ;; *) [ -e $f ] || ln -s $(readlink -f $BUNDLE/$f) $f;; esac; done
rm -rf slice; ln -s $DIR/slice slice
python3 flatten_masters.py --bundle . --views views.json --hier 0 --nohier "" --verilator "$VL" > $DIR/flatten.log 2>&1 || { tail $DIR/flatten.log; exit 3; }
sed 's#^#masters/#; s#$#.sv#' slice/masters.txt > $DIR/masters.f
/usr/bin/time -v -o $DIR/build.time $VL --cc --exe --main --timing --build -j $JOBS -O1 --top-module tb_collar -Mdir $DIR/obj \
  -Wno-fatal -Wno-lint -Wno-style -Wno-MODDUP -Wno-PINMISSING -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
  -Wno-INITIALDLY -Wno-COMBDLY -Wno-BLKANDNBLK -Wno-SELRANGE -Wno-WIDTH -Wno-CASEINCOMPLETE \
  --x-initial unique --x-assign unique -f $DIR/masters.f slice/slice.v $DIR/tb_collar.sv > $DIR/build.log 2>&1 || { grep -m8 %Error $DIR/build.log; exit 2; }
python3 $(dirname $(readlink -f $0))/../verilator_nba_guard.py $DIR/obj | tee $DIR/nba_guard.log | grep -q "INPLACE_NBA_LOOPS=0" || { echo "VERILATOR_NBA_GUARD FAIL"; exit 86; }
$DIR/obj/Vtb_collar +verilator+rand+reset+2 > $DIR/run.log 2>&1; RC=$?
grep -E "COLLAR_(CHECK|BENCH)|ROWV_ALIGN" $DIR/run.log; echo "EXIT rc=$RC"
