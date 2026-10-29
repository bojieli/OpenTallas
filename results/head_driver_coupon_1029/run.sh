#!/bin/bash
set -eu
cd "$(dirname "$0")"
docker run --rm --name codex-head-driver-coupon-libs --memory=1g --memory-swap=1g --cpus=1 --user "$(id -u):$(id -g)" -v "$PWD":/work openroad/orfs:asap7lock bash -lc '
set -eu
for corner in TT FF;do
 gzip -dc /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${corner}_nldm_220122.lib.gz > /work/INVBUF_${corner}.lib
done
'
for corner in TT FF;do CORNER=$corner sta -exit coupon.tcl > coupon_$corner.log 2>&1;done
