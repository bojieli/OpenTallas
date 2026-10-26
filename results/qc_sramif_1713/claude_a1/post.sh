#!/bin/bash
# PATH-QC-SRAMIF2 post-place: placed.csv + r2r census + render for kit $1 (title $2)
set -uo pipefail
R=/srv/opentallas-scratch2/claude/path-qc-sramif2; k=$1; K=$R/$k; N=$(basename $(dirname $(ls -d $K/run/results/asap7/*/base)))
docker run --rm --memory=8g -v $R:/w openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; ODB=/w/$k/run/results/asap7/$N/base/3_place.odb OUT=/w/$k/placed.csv openroad -python -exit /w/$k/dump_placed.py >/dev/null; ODB=/w/$k/run/results/asap7/$N/base/3_place.odb OUT=/w/$k/r2r_3_place.json openroad -python -exit /w/r2r_reach.py 2>&1 | grep R2R; chown -R $(id -u):$(id -g) /w/$k"
python3 $R/render_a1.py $K "$2" $K/${k}_place.png
grep -h VERDICT $K/f6_3_place/F6_TABLE.tsv; awk -F'\t' 'NR>1 && $1=="F6"{if($6>m)m=$6}END{print "F6 max",m}' $K/f6_3_place/F6_TABLE.tsv; tail -n1 $K/keep_check.txt
