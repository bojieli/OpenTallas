#!/bin/bash
# DIE-QC-4 stage 2: kit signal GRT with the frozen stage-1 clock route as 5-track obstructions. usage: runSig.sh KITNAME NDR
set -u
B=/srv/opentallas-scratch2/claude/die-qc4-1028; K=$B/$1; N=$2; O=$K/c2_$N
mkdir -p $O
CORNER=TT python3 -I $B/mk_clkfirst_qc.py $K/trial $K/clk $O sig $K/c1_${N}_TT/route_TT.guide 5 > $O/mk.log 2>&1 || { echo MK_FAIL; exit 1; }
docker run --rm --name qc4s-$1-$N --memory=64g --memory-swap=64g --cpus=16 -v $K/trial:/work:ro -v $O:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 16 -exit /out/sig.tcl > /out/sig.log 2>&1; echo EXIT \$? >> /out/sig.log; chown -R $(id -u):$(id -g) /out"
echo "sig $1 $N $(tail -1 $O/sig.log) $(date)" >> $B/chain.log
