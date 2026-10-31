#!/bin/bash
# HBM-HUBMESH-2 post-GRT chain: rec -> mesh mc 60 TT -> hub-only proof -> die_sta_related (12.25) -> contract split
# usage: post.sh PART ORIGIN_X ORIGIN_Y   (run in the hub-mesh-2 dir on the host holding a2/kit/mesh/PART)
set -x
P=$1; OX=$2; OY=$3; V=${V:-a3rp}
D=/srv/opentallas-scratch2/claude/hbm-hubmesh-3; W=/srv/opentallas-scratch2/claude/wt/hbm-hubmesh-3
T=$D/$V/kit/mesh/$P; R=$D/post_${V}_$P; mkdir -p $R
PLAN=/srv/opentallas-scratch2/claude/hbm-clkloc-1/in/d44f/die_plan.json
cd $W && python3 tools/clk/ot_clk.py rec tools/clk/configs/hbm_hubmesh_$V.yaml --trial $T --stage grt > $R/rec.log 2>&1 || exit 1
docker run --rm --name hbmhm3-mc-$P-$$ --memory=24g --cpus=8 -v $W:$W -v $D:$D -v /srv/opentallas-scratch2/claude/hbm-hubmesh-1/pylib:/pylib \
  -e PYTHONPATH=/pylib openroad/orfs:asap7lock bash -lc "python3 $W/tools/die_plan/explicit_mesh_signoff.py mc $T/rec_grt.json --thev $W/results/die_hbm_1031/hubmesh1/thev_m1.json --corner TT --samples 60 --out $R/mc_TT.json > $R/mc_TT.log 2>&1; echo EXIT \$? >> $R/mc_TT.log; chown -R 1000:1000 $R"
python3 $W/results/die_hbm_1031/hubmesh2/mk_hubproof.py $R/mc_TT.json $T/rec_grt.json $P $OX $OY $R/proof || exit 1
cd $D && (ulimit -v 32000000; PYTHONPATH=$W/tools/die_plan python3 $W/tools/die_plan/die_sta_related.py $R/proof --plan $PLAN --out $R/sta --clock-cell buf --clock-cal none --clock-ocv none --cppr-lca --core-latency-ff 202.5 > $R/sta.log 2>&1)
python3 $W/results/die_hbm_1031/hubmesh2/contract_split.py $R/proof $PLAN 0 40 60 80 120 160 200 260 > $R/contract_split.txt 2>&1
echo POST_DONE
