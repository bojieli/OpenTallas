#!/bin/bash
# DIE-QC-4 stage-1 clock-first GRT (clock alone, macros + PG as blockages, optional CK2W2S NDR). usage: runC.sh KITNAME NDR CORNER
set -u
B=/srv/opentallas-scratch2/claude/die-qc4-1028; K=$B/$1; N=$2; C=$3; O=$K/c1_${N}_$C
mkdir -p $O
CORNER=$C python3 -I $B/mk_clkfirst_qc.py $K/trial $K/clk $O clk $N > $O/mk.log 2>&1 || { echo MK_FAIL; exit 1; }
docker run --rm --name qc4c-$1-$N-$C --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K/trial:/work:ro -v $O:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/clk.tcl > /out/clk_$C.log 2>&1; echo EXIT \$? >> /out/clk_$C.log; chown -R $(id -u):$(id -g) /out"
echo "done $1 $N $C $(tail -1 $O/clk_$C.log) $(date)" >> $B/chain.log
