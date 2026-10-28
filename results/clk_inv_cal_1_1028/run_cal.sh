#!/bin/bash
# CLK-INV-CAL-1: inverter MC (clk_aocv_mc method) + spice-vs-OpenSTA comb trees, intel1 docker, 1 CPU / 1-4 GB each
set -u
M=/srv/opentallas-scratch2/claude/clk-inv-cal-1-1028; cd $M; P=${P:-44}
log(){ echo "$1 $(date)" >> $M/run.log; }
rm -rf run/tInv_TT
seed=30
for spec in "250 400" "150 200"; do set -- $spec; for c in TT FF; do seed=$((seed+1))
  python3 -I clk_inv_cal.py mcgen --lib $M/lib --out $M/run/Ainv${1}_$c --cls Ainv$1 --corner $c --wire-um $1 --samples $2 --depth 8 --seed $seed
done; done
# trees: inverter 250/150 NDR, 250 1x, BUFx24 450 NDR control
python3 -I clk_inv_cal.py treegen --out $M/tree/inv250 --cell inv --wire-um 250
python3 -I clk_inv_cal.py treegen --out $M/tree/inv150 --cell inv --wire-um 150
python3 -I clk_inv_cal.py treegen --out $M/tree/inv250x1 --cell inv --wire-um 250 --rc 1x
python3 -I clk_inv_cal.py treegen --out $M/tree/buf450 --cell buf --wire-um 450 --stages 40 --every 2 --branch 2
log GEN
for t in tree/*; do for c in TT FF; do
  docker run --rm --memory 2g -u $(id -u):$(id -g) -v $M/$t:/d -w /d openroad/orfs:asap7lock sh -c "zcat /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${c}_nldm_220122.lib.gz > lib_${c}.lib; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -no_splash -exit sta_${c}.tcl" > $M/$t/sta_${c}.log 2>&1
done; done
log STA
( ls tree/*/deck_*.sp | xargs -P 8 -I{} sh -c 'd=$(dirname {}); b=$(basename {} .sp); docker run --rm --name clkinv-$(basename $d)-$b --memory 4g --cpus 1 -u '$(id -u):$(id -g)' -v '$M':/w -w /w/$d ot-ngspice:r3 sh -c "ngspice -b $b.sp > $b.log 2>&1"'; log TREES ) &
ls run/Ainv*/s*.sp | sed 's#^run/##' | xargs -P $P -I{} sh -c 'd=$(dirname {}); b=$(basename {} .sp); docker run --rm --name clkinv-$d-$b --memory 1g --cpus 1 -u '$(id -u):$(id -g)' -v '$M':/w -w /w/run/$d ot-ngspice:r3 sh -c "ngspice -b $b.sp > $b.log 2>&1"'
python3 -I clk_inv_cal.py mcparse run/Ainv250_TT run/Ainv250_FF run/Ainv150_TT run/Ainv150_FF --out $M/mc_inv.json
python3 -I clk_inv_cal.py mcfit $M/mc_inv.json --out $M/inv_rows.json > $M/mcfit.txt 2>&1
rm -f run/*/s*.log
log MCDONE
wait
for t in tree/*; do for c in TT FF; do python3 -I clk_inv_cal.py compare $t --corner $c >> $M/compare.txt 2>&1; done; done
log ALLDONE
