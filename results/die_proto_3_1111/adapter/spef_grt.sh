#!/bin/bash
# DIE-PROTO-3: re-run the die combo GRT (TT) with estimate_parasitics -spef_file, then build the die_ctree adapter dir
# usage: spef_grt.sh DIE_RUN_DIR (holds kit/, grt_st_TT/)  [GM]
set -u; R=$1; GM=${2:-32g}; W=/srv/opentallas-scratch2/claude/wt/die-proto-3; T=$W/tools/clk/ot_clk_die_ctree.py
K=$R/kit; S=$R/grt_spef_TT; mkdir -p $S
cp $R/grt_st_TT/combo.v $R/grt_st_TT/combo.tcl $S/
python3 -I $T tcl $S/combo.tcl /out/combo_TT.spef || exit 2
docker run --rm --name dproto3-spef-$(basename $(dirname $R))-$(basename $R) --memory=$GM --memory-swap=$GM --cpus=8 -e CORNER=TT \
  -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $S:/out openroad/orfs:latest \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_TT.log 2>&1; echo EXIT \$? >> /out/combo_TT.log; chown -R 1000:1000 /out"
tail -n1 $S/combo_TT.log
python3 -I $T build --ctree-v $K/clock/ctree.v --spef $S/combo_TT.spef --out $R/die_ctree --tree $K/clock/tree.json
echo "ADAPT rc=$?"
