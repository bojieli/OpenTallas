#!/bin/bash
# QC-MESH-PILOT-1: rec -> MC TT/FF (explicit_mesh_signoff, docker ot-ngspice:r3 8 GB) -> pair, for TRIAL STAGE
# usage: pilot_chain.sh TRIAL_DIR STAGE   (run in the pilot data dir; thev_m1.json there)
set -e
T=$1; ST=$2; S=$(cd $(dirname $0) && pwd); W=$(cd $S/../.. && pwd); D=$(pwd)
A14=/srv/opentallas-scratch2/claude/die-qc21-1028
python3 $S/pilot_signoff.py rec $T $ST
for C in TT FF; do
  docker run --rm --name qcmp-mc-$(basename $T)-$ST-$C --memory=8g --cpus=8 -v $W:$W -v $D:$D -w $D ot-ngspice:r3 \
    python3 $W/tools/die_plan/explicit_mesh_signoff.py mc $T/rec_$ST.json --thev thev_m1.json --corner $C --samples 60 --jobs 8 --out $T/mc_${ST}_$C.json | tail -1
done
python3 $S/pilot_signoff.py pair $T $ST $A14/c14_TT/arr_TT.txt $A14/c14_FF/arr_FF.txt
