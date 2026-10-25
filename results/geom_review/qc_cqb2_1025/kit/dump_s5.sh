#!/bin/bash
# QC-CQB2 vmr_s5 render dumps: dump_s5.sh OUTDIR grt|spef ODB GUIDE_or_SPEF VCLK_LAT  (TT + FF, docker, RC-calibrated for grt)
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); O=$1; P=$2; ODB=$3; G=$4; V=$5; IMAGE=openroad/orfs:asap7lock
mkdir -p "$K/$O"
for c in tt ff; do
  docker run --rm --name qccqb2-s5-dump-$c-$$ --cpus=4 --memory=8g --memory-swap=8g -v "$K":/work -w /work \
    -e OT_CORNER=$c -e ODB=$ODB -e PAR=$P -e GUIDE=$G -e SPEF=$G -e VCLK_LAT=$V -e OT_RC_CAL=0.8,0.9 -e OUT=/work/$O/dump_$c.tsv $IMAGE \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 4 -exit /work/geom_dump_s5.tcl" > "$K/$O/dump_$c.log" 2>&1 &
done
wait
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work/$O >/dev/null 2>&1
cp run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base/ot_macro_pin_flops.txt run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base/ot_face_flops.txt "$K/$O/" 2>/dev/null
ls -la "$K/$O"
