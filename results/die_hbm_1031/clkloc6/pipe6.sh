#!/bin/bash
# HBM-CLKLOC-6 copy of pipe5.sh (wt hbm-clkloc-6): kit -> route TT/FF -> proof -> composite with the hub MESH a3e6s -> 12.25 single gate + per-tag breakdown
# -> head_mk_proof_lca -> die_sta_related (spice_edge, cppr-lca, OCV table, shared droop, HB4). usage: pipe.sh C1|C2 CELL
set -u; export OT_CLK_DME_LOG=1
V=$1; CELL=$2; R=/srv/opentallas-scratch2/claude/hbm-clkloc-1; W=/srv/opentallas-scratch2/claude/wt/hbm-clkloc-6
D=$R/$V; mkdir -p $D; cd $D; ulimit -v 96000000
CFG=$W/tools/clk/configs/hbm_d44f_clkloc_$(echo $V | tr A-Z a-z).yaml
echo "start $(date)" >> $V.status
python3 $W/tools/clk/ot_clk.py kit $CFG --out $D/k1 --workers 16 > kit.log 2>&1; rc=$?; echo "kit rc $rc $(date)" >> $V.status; [ $rc = 0 ] || exit 1
K=$D/k1/kit
route() { C=$1; O=$D/run/out_$C; mkdir -p $O $D/run/clk; cp $K/clock/tree.json $K/clock/ctree.v $D/run/clk/
  CORNER=$C python3 $R/in/mk_clkfirst.py $K $K/clock $O clk 2w2s > $O/mk.log 2>&1
  docker run --rm --name hclkloc-$V-$C-$$ --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; set +e; openroad -no_init -threads 8 -exit /out/clk.tcl > /out/clock.log 2>&1; rc=\$?; echo EXIT \$rc >> /out/clock.log; chown -R $(id -u):$(id -g) /out; exit \$rc"; }
(route TT > route_TT.log 2>&1; echo "route TT rc $? $(date)" >> $V.status) & (route FF > route_FF.log 2>&1; echo "route FF rc $? $(date)" >> $V.status) & wait
python3 $W/tools/s81_head/head_mk_proof_lca.py $D/run $D/k1/ot_clk_regions_street_part_region.json $D/proof > proof.log 2>&1; echo "proof rc $? $(date)" >> $V.status
# CLKLOC-6: die-tree proof + hub mesh a3e6s (T028/T029 hub taps = die node arrival + routed mesh), then 12.25 single gate
python3 $R/mk_composite.py $D/proof $D/cproof NW_hub:T028:$R/in/mesh_a3e6s/NW_hub NE_hub:T029:$R/in/mesh_a3e6s/NE_hub > $D/composite.log 2>&1; echo "composite rc $? $(date)" >> $V.status
$R/gate6t.sh $D/cproof $D/all_mesh; echo "gate done $(date)" >> $V.status
