#!/bin/bash
# MODEL-REFIT-2: collect btab_m0_r4 routed RCX clock latency (run on intel2 after route_r4.log ends without STAGE_FAIL).
# meas_ck.tcl on 6_final ODB/SDC/SPEF for TT and FF (read-only kit mount, docker 12g), then resid.py vs the as-built json,
# and the GRT->RCX per-leaf delta against meas_ck on 5_1_grt.odb (btab_r4/meas_ck_{TT,FF}.tsv, same script).
K=/srv/opentallas-scratch2/claude/qc-su-kits2-1026/btab_m0_r4; B=run/results/asap7/kq_qfd_dv_s8x_btab_mif0k2/base
O=/srv/opentallas-scratch2/claude/model-refit2-1026/btab_r4_rcx; T=/srv/opentallas-scratch2/claude/model-refit2-1026/tools
mkdir -p $O; grep -q STAGE_FAIL $K/route_r4.log && { echo "STAGE_FAIL in route_r4.log"; exit 1; }
for f in 6_final.odb 6_final.sdc 6_final.spef; do [ -f $K/$B/$f ] || { echo "missing $f"; exit 1; }; done
for C in TT FF; do
 timeout 1800 docker run --rm --memory=12g --memory-swap=12g --cpus=2 -v $K:/work:ro -v $O:/out -v $T/meas_ck.tcl:/m.tcl:ro \
  -e ODB=/work/$B/6_final.odb -e SDC=/work/$B/6_final.sdc -e SPEF=/work/$B/6_final.spef -e OT_CORNER=$C -e OUT=/out/meas_rcx_$C.tsv \
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /m.tcl" > $O/meas_rcx_$C.log 2>&1 &
done; wait
docker run --rm -v $O:/out openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /out
grep -h MEAS_DONE $O/*.log
# then (any host with the repo): python3 results/qc_su_kits/r4/prog_m0_r3_build/resid.py meas_rcx_TT.tsv meas_rcx_FF.tsv \
#   results/qc_su_kits/r4/btab_m0_r4/btab_ls_k6_L3.gate.asbuilt.json btab_m0_r4_rcx_resid.json
# GRT->RCX: per-leaf mean(meas_rcx) - mean(meas_ck GRT) with common.parse_sinks (results/model_refit2_1026/py/common.py)
