#!/bin/bash
# CLK-AOCV MC: 4 configs x N samples, depth 6, one capped container per deck, 48 in parallel
set -e
W=/srv/opentallas-scratch2/claude/wt/claude-clk-aocv-1026; M=/srv/opentallas-scratch2/claude/clk-aocv-1026/mc; cd $M; rm -rf run/t* run/[AB]_*
N=${N:-400}; seed=11
for ch in A B; do for c in TT FF; do seed=$((seed+1))
  python3 $W/tools/die_plan/clk_aocv_mc.py gen --lib $M/lib --out $M/run/${ch}_$c --chain $ch --corner $c --samples $N --depth 6 --seed $seed
done; done
ls run/*/s*.sp | sed 's#^run/##' | xargs -P 48 -I{} sh -c 'd=$(dirname {}); b=$(basename {} .sp); docker run --rm --name clkaocv-$d-$b --memory 1g --cpus 1 -v '$M':/w -w /w/run/$d ot-ngspice:r3 sh -c "ngspice -b $b.sp > $b.log 2>&1; chown $(id -u):$(id -g) $b.dat $b.log 2>/dev/null; true"'
python3 $W/tools/die_plan/clk_aocv_mc.py parse run/A_TT run/A_FF run/B_TT run/B_FF --out $M/mc_raw.json
rm -f run/*/s*.log
echo MCDONE $(date)
