#!/bin/bash
# build.sh TAG ASM_TOP TB.sv ASM.v [extra piece files...] : Verilator lock-step front-end (PATH-HBM/Q3 10-25)
# FILES = master file list (default ../q3synth/q3.files; q3b.files adds ot_hgi_coll_edge_pr.sv).  Verilates only
# (no --build): the 48 vm_classes amalgamations needed >13 GB per cc1plus, so comp_ind.sh compiles one .cpp per unit.
TAG=$1; ATOP=$2; TB=$3; ASM=$4; shift 4
D=/srv/opentallas-scratch2/claude/path-hbm/q3split; WT=/srv/opentallas-scratch2/claude/wt/path-hbm-q3-1025
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
cd $D; mkdir -p obj_$TAG
F=$(grep -v "^macro:" ${FILES:-../q3synth/q3.files} | sed "s,^,$WT/," | tr "\n" " ")
for m in ot_sram_1r1w_64x512_m1_r2c2 ot_sram_1rw_256x64_m4_r2c2 ot_sram_1r1w_256x256_m2_r2c2; do F="$F $WT/physical/asap7_memory_macros_v2/$m/$m.v"; done
/usr/bin/time -v $V --cc --exe --main --timing --top-module tb -Mdir obj_$TAG -o sim -O0 --x-assign 0 --x-initial 0 \
  -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-TIMESCALEMOD \
  -DSYNTHESIS -DOT_COLL_ISSUER256_NATIVE32 --output-split 20000 --output-split-cfuncs 2000 \
  $F "$@" $ASM $TB > build_$TAG.log 2>&1
echo "build $TAG rc=$?"
