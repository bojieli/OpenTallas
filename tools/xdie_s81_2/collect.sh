#!/bin/bash
# XDIE-S81-2 collect (run LOCALLY in a worktree of claude/xdie-s81-2-1019, after the 4 ot-run jobs printed "RAN on"):
#   bash tools/xdie_s81_2/collect.sh <worktree> <otrun log dir>
# Pulls the verdict files + gzipped run logs of out_{c,a,m,w} from the host each job ran on, writes
# results/rtl/xdie_s81_1019/{gate/*, record.json} (record.py --compose: token_compose block from the gate's `min` run),
# then re-composes results/arch/token_path_1018 and runs tools/token_compose_xdie.py --check.
set -eu
W=$1; LD=$2
R=/srv/opentallas-scratch/claude/xdie-s81-2/stage
D=$W/results/rtl/xdie_s81_1019; mkdir -p $D/gate $D/tmp
for j in c a m w m2; do
  h=$(grep -oE "RAN on [a-z0-9-]+" $LD/otrun_$j.log | awk '{print $3}' | tail -1)
  [ -n "$h" ] || { echo "job $j has not RUN yet ($LD/otrun_$j.log)"; exit 2; }
  ssh -o BatchMode=yes $h "cd $R/out_$j && for n in */run.log; do gzip -c \$n > \${n%/run.log}.run.log.gz; done; ls" > /dev/null
  rsync -a --include='*.txt' --include='*.run.log.gz' --include='*/' --include='verilator_version.txt' --exclude='obj/' \
    --exclude='*' $h:$R/out_$j/ $D/tmp/out_$j/
  # job m = the first MU runs on the fmt0 goldens (random TP payload in the lep tag field [1077:1045]: FINDING, kept as
  # *.fmt0.*); job m2 = the same binary on the regenerated goldens (gen_golden MU_SPARE) -> the canonical mu_* verdicts
  for f in $D/tmp/out_$j/*.txt $D/tmp/out_$j/*.run.log.gz; do [ -f $f ] || continue; b=$(basename $f)
    case "$j:$b" in m:mu_*) cp $f $D/gate/${b%%.*}.fmt0.${b#*.};; *) cp $f $D/gate/;; esac; done
  cp $D/tmp/out_$j/b*/verilator_version.txt $D/gate/verilator_$j.txt 2>/dev/null || true
done
S=/home/ubuntu/scratch/xdie-s81-2/stage
cp $S/SOURCES.txt $D/SOURCES.txt
mkdir -p $D/golden; for g in g556 g564 gm564 mr md mm mr_fmt0 md_fmt0; do cp $S/goldens/$g/golden.json $D/golden/$g.json; sha256sum $S/goldens/$g/stim.hex | awk -v g=$g '{print $1, g "/stim.hex"}'; done > $D/golden/stim.sha256
for n in min min_err mu_real mu_dense noleg; do gunzip -c $D/gate/$n.run.log.gz > $D/tmp/$n.log; done
cd $W
python3 tools/xdie_s81_2/record.py --golden $S/goldens/g564/golden.json --run $D/tmp/min.log --name gate_min_current_rtl \
  --out $D/record.json --dag results/arch/token_path_20261009/ds_rom.json --dag-mtp results/arch/token_path_20261009/ds_rom_mtp.json \
  --compose --commit "G8R2 0e6b9b710 + HF-3 lane ed9d570ad + MU lep main (stage SOURCES.txt), Verilator 5.050" \
  --mu mu_real=$S/goldens/mr:$D/tmp/mu_real.log --mu mu_dense=$S/goldens/md:$D/tmp/mu_dense.log \
  --extra-run min_err=$D/tmp/min_err.log --extra-run noleg_gate_g5_form=$D/tmp/noleg.log
# fixed-latency check (lfix_check.py): the bench bounds landings only from above; the die's crossing latency is fixed
for n in min min_err chb0 late asbound landsel mu_real mu_dense mu_dense_err wrongcopy tagdrop; do
  echo "$n $(python3 tools/xdie_s81_2/lfix_check.py $D/gate/$n.run.log.gz --lfix 563)"; done > $D/gate/lfix.txt
python3 tools/xdie_s81_2/lfix_check.py $D/gate/noleg.run.log.gz --lfix 553 | sed 's/^/noleg /' >> $D/gate/lfix.txt
rm -rf $D/tmp
python3 tools/token_compose_xdie.py
python3 tools/token_compose_xdie.py --check
