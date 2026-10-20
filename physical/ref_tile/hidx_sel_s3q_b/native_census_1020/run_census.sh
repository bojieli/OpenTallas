#!/bin/bash
# usage: run_census.sh <gate_dir> <top> <outjson>  (runs on the fleet host holding gate_dir; ORFS docker image libs)
G=$1; TOP=$2; OUT=$3; T=$(dirname $(readlink -f $0))
NL=$(ls $G/routes/gate/work/orfs/results/asap7/*/base/1_2_yosys.v | head -1)
MLIBS=""; for m in $(grep -oE '^\s+[A-Za-z_][A-Za-z0-9_]*\s' $NL | awk '{print $1}' | sort -u | grep -v -E 'ASAP7|^(wire|input|output|module|assign|endmodule)$'); do
  f=$(find $G/src $G/routes/gate/work/orfs/results -name "$m*.lib" ! -name '*_pre_layout.lib' 2>/dev/null | grep -v -i -E '_(ff|ss)(_|\.)' | head -1); [ -n "$f" ] && MLIBS="$MLIBS ${f/#$G//g}" || echo "NO_LIB $m"; done
ARGS=""; for l in $MLIBS; do ARGS="$ARGS --liberty $l"; done
docker run --rm -u $(id -u):$(id -g) -v $G:/g:ro -v $T:/t -v $(dirname $OUT):/o openroad/orfs:asap7lock bash -c "
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM; LA=''; for f in \$L/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_{RVT,LVT}_TT_nldm_*.lib*; do LA=\"\$LA --liberty \$f\"; done
python3 /t/tools/ref_tile/native_census.py --netlist /g/${NL#$G/} --top $TOP --out /o/$(basename $OUT) \$LA $ARGS"
