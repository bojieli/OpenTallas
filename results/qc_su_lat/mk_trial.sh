#!/bin/bash
# mk_trial.sh SRC_KIT DST VARIANT  -- copy a core kit (results only up to 3_place), apply QC-SU-LAT clock knobs
set -euo pipefail
S=$1; D=$2; V=$3
mkdir -p $D
rsync -a --exclude 'run/results/*/*/base/4_*' --exclude 'run/results/*/*/base/5_*' --exclude 'run/results/*/*/base/6_*' \
  --exclude 'run/results/*/*/base/*.guide' --exclude 'run/logs/*/*/base/4_*' --exclude 'run/logs/*/*/base/5_*' --exclude 'run/logs/*/*/base/6_*' \
  --exclude 'hold_checkpoints' --exclude 'signoff' --exclude 'so_exact' --exclude 'f6_*' --exclude 'run/reports' --exclude 'run/objects/*/*/base/*.odb' $S/ $D/
cd $D
sed -i '/^export OT_MSCTS_SEG_UM/d; /^export OT_MSCTS_LEG_SEG_UM/d; /^export OT_MSCTS_TRUNK_CELL/d' config.mk
case $V in
 A) printf '# QC-SU-LAT variant A (2026-10-26): long equal-stage trunk (110 um, BUFx16f) -> fewer trunk stages\nexport OT_MSCTS_SEG_UM = 110\nexport OT_MSCTS_LEG_SEG_UM = 120\nexport OT_MSCTS_TRUNK_CELL = BUFx16f_ASAP7_75t_R\n' >> config.mk ;;
esac
echo "trial $V from $S $(date -Is)" > image.txt
