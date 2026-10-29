#!/bin/bash
# DIE-QC-31: splice ECO c1 nets -> RCX -> re-time all clips -> compose rise/fall -> rec -> MC 60 (TT/FF, both edges) -> pair U
set -euo pipefail
W=/srv/opentallas-scratch2/claude/die-qc31; V=$1; D=$W/v$V; B=$W/base
S=$B/mcin/codex-qc-mesh-1029/mc_src
echo "START $(date)"
rm -rf $D/a3 $D/pilot_mc; cp -a $B/a3 $D/a3; mkdir -p $D/pilot_mc/tA3d $D/pilot_mc/tA3d_fall
python3 $W/splice.py $B/a3/c1/drt.def $D/c1eco/eco.def $D/a3/c1/drt.def n_P1u,n_B1
rm -f $D/a3/c1/drt.spef $D/a3/c1/drt.odb
docker run --rm --name dieqc31-rcx-$V --memory=16g --memory-swap=16g --cpus=4 -e SLEW=67.00679 -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $W:$W -v $D/a3/c1:/o -w $W openroad/orfs:asap7lock bash -lc \
  'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit rcx.tcl > /o/rcx.log 2>&1; rc=$?; chown -R 1000:1000 /o; exit $rc'
grep -q OT_RCX_DONE $D/a3/c1/rcx.log
sed 's/dieqc30-qcmp3/dieqc31-sta-'$V'/' $B/ready_sta.sh > $D/ready_sta.sh; chmod +x $D/ready_sta.sh
$D/ready_sta.sh $D/a3 > $D/sta.log 2>&1
for C in TT FF; do
  python3 $B/pilot_clip.py compose $B/trial/tA3 $D/a3 drt $C $D/pilot_mc/tA3d/tree_drt_$C.txt
  python3 $B/pilot_clip.py compose $B/trial/tA3 $D/a3 drt ${C}_fall $D/pilot_mc/tA3d_fall/tree_drt_$C.txt
done > $D/compose.log 2>&1
for T in tA3d tA3d_fall; do cp $B/pilot_mc/tA3d/pilot.json $D/pilot_mc/$T/; python3 $S/results/qc_mesh_pilot_1/pilot_signoff.py rec $D/pilot_mc/$T drt; done > $D/rec.log 2>&1
cp $B/pilot_mc/thev_m1.json $D/pilot_mc/
cd $D/pilot_mc
for T in tA3d tA3d_fall; do for C in TT FF; do
  docker run --rm --name dieqc31-mc-$V-$T-$C --memory=8g --memory-swap=8g --cpus=8 -v $W:$W -w $D/pilot_mc ot-ngspice:r3 \
    python3 $S/tools/die_plan/explicit_mesh_signoff.py mc $T/rec_drt.json --thev thev_m1.json --corner $C --samples 60 --jobs 8 --out $T/mc_drt_$C.json > $T/mc_$C.log 2>&1 &
done; done
wait
for T in tA3d tA3d_fall; do python3 $S/results/qc_mesh_pilot_1/pilot_signoff.py pair $T drt $B/mcin/die-qc21-1028/c14_TT/arr_TT.txt $B/mcin/die-qc21-1028/c14_FF/arr_FF.txt; done > $D/mc.log 2>&1
echo "DONE $(date)" >> $D/mc.log
