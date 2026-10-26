#!/bin/bash
# run_post.sh CORNER [SKIP_PS]  -- diagnostic post-CTS check (docker, 16 GB cap) on the t1 kit
K=/srv/opentallas-scratch2/claude/cores-kits/kvx/pv_pair/t1; c=$1; U=$(echo $c | tr a-z A-Z)
P=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
docker run --rm --name kvx-pvp-post-$c-$$ --memory=16g --cpus=4 -u $(id -u):$(id -g) -v $K:/work ${2:+-e OT_SKIP_PS=1} \
  -e OUTD=/work/postcts -e OT_CORNER=$c -e OT_VCLK_TT=250 -e OT_VCLK_FF=202.5 -w /work openroad/orfs:asap7lock bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; export OT_LIBS=\"\$(ls $P/asap7sc7p5t_*RVT_${U}_*.lib* | grep -v FAKE | tr '\n' ' ') /work/macros/ot_sram_1r1w_32x128_m1_$c.lib\"; openroad -exit /work/postcts/postcts.tcl"
