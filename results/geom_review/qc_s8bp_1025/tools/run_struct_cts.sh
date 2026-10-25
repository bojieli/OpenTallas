#!/bin/bash
# run_struct_cts.sh KIT EST(placement|grt) SRAMBASE [CPUS] [MEM] : structured CTS (+GRT) on KIT 3_place.odb -> 4_cts.odb,
# then independent TT/FF GRT measurement of the result (meas.tcl reads 5_1_grt.odb; we write the CTS+GRT DB there)
set -u
K=$1; EST=$2; SRAM=$3; C=${4:-4}; M=${5:-16}
N=$(ls -d $K/run/results/asap7/*/base | head -1); NICK=$(basename $(dirname $N))
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name s8bp-cts-$(basename $K) --cpus=$C --memory=${M}g --memory-swap=${M}g -v $K:/work \
  -e OT_STAGE_IN=/work/run/results/asap7/$NICK/base/3_place.odb -e OT_SDC_IN=/work/run/results/asap7/$NICK/base/3_place.sdc \
  -e OT_OUT_ODB=/work/run/results/asap7/$NICK/base/4_cts.odb -e OT_OUT_SDC=/work/run/results/asap7/$NICK/base/4_cts.sdc \
  -e OT_OUT_GUIDE=/work/run/results/asap7/$NICK/base/route.guide \
  -e OT_SRAM_LIB=/work/macros/${SRAM}_tt.lib -e OT_EST=$EST openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/struct_cts.tcl > $K/struct_cts.log 2>&1
rc=$?; echo "struct_cts rc $rc $(date)"
[ $rc = 0 ] || exit $rc
cp $K/run/results/asap7/$NICK/base/4_cts.odb $K/run/results/asap7/$NICK/base/5_1_grt.odb
cp $K/run/results/asap7/$NICK/base/4_cts.sdc $K/run/results/asap7/$NICK/base/5_1_grt.sdc
mkdir -p $K/meas
for c in tt ff; do
 $DK run --rm --name s8bp-meas-$(basename $K)-$c --memory=12g --memory-swap=12g --cpus=2 -v $K:/src:ro -v $K/meas:/out \
  -e OT_CORNER=$c -e SRC=/src -e NICK=$NICK -e SRAM=$SRAM -e OUT=/out openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/meas.tcl > $K/meas/meas_$c.log 2>&1 &
done; wait
cp $K/meas.tcl $K/meas/ 2>/dev/null; echo "meas done $(date)"
