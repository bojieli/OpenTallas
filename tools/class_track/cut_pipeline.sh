#!/bin/bash
export PATH=$HOME/.local/bin:/usr/local/bin:$PATH
set -u
# CLASS-TRACK cut pipeline (hub intel2).  usage: cut_pipeline.sh "2026-11-26 21:00 PST" [dry]
# 1 live plans from kit_wave.json -> 2 PRE (plan_advisory) + RSTREACH per die via ot-run on kit hosts -> 3 class_track cut against the hub
# CLASS-TREND with the 09:00 carry rows marked CARRIED (not re-measured: shown, never a fall/rise) -> 4 commit CLASSES/MAP/TREND and post
# RESULT; LOOP to COORD with the per-class breakdown when HEAD/QC/FLEET (any die) is flat for the second cut.
set -u
LABEL="$1"; DRY="${2:-}"
S2=/srv/opentallas-scratch2/claude; B=$S2/CLASS-TRACK; T=$B/wt/tools/class_track; C=$HOME/coord
TAG=$(echo "$LABEL" | tr -c 'A-Za-z0-9' '_'); D=$B/cut_$TAG; mkdir -p $D/pre; cd $D
python3 -I $T/class_track.py plans --kit-wave $C/autopilot/kit_wave.json > live_plans.tsv
CK="FP-FLOORPLAN,LEG405-ZERO,TAP-LOAD,RELAY-SEAT,RAW-RESET-TO-PORT,LAND-REACH"
HOSTS=intel1,epyc7,epyc8,epyc10,epyc11
tail -n +2 live_plans.tsv | while IFS=$'\t' read die plan tree asb bind; do
  d=$(echo $die | tr A-Z a-z); [ "$plan" = "-" ] && continue
  A=$asb; [ "$A" = "-" ] && A=-
  ST=""; EL=-; if [ "$bind" != "-" ]; then ST="--stage $bind"; EL=$bind; fi
  nohup ot-run --mem 48 --threads 4 --dir $tree --disk 5 --hosts $HOSTS --stage $B --stage $S2/rt/current/tools/die_plan $ST -- bash $B/pre_cut2.sh $d $plan $tree $A $CK $B/pre_$TAG > $D/pre_$d.log 2>&1 &
  nohup ot-run --mem 32 --threads 2 --dir $tree --disk 5 --hosts $HOSTS --stage $B --stage $S2/rt/current/tools/die_plan $ST -- bash $B/rst_cut.sh $d $plan $tree $EL $B/pre_$TAG > $D/rst_$d.log 2>&1 &
done
# wait for the 8 jobs (max 50 min), then collect the outputs from whichever host ran them
for i in $(seq 1 100); do
  n=0; for h in ${HOSTS//,/ }; do n=$((n+$(ssh -n -o ControlPath=none -o ConnectTimeout=10 $h "cat $B/pre_$TAG/done.txt 2>/dev/null | wc -l" 2>/dev/null || echo 0))); done
  [ "$n" -ge 8 ] && break; sleep 30
done
for h in ${HOSTS//,/ }; do scp -q -o ControlPath=none "$h:$B/pre_$TAG/*" $D/pre/ 2>/dev/null; done
for d in s81 head qc kv; do [ -f pre/$d.sha ] && echo "$d $(cat pre/$d.sha)"; done > shas.txt
printf 'die\tplan_sha12\n' > plans.tsv; for d in s81 head qc kv; do printf '%s\t%s\n' "$(echo $d | tr a-z A-Z)" "$(cat pre/$d.sha 2>/dev/null || echo unknown)" >> plans.tsv; done
# carry: every 09:00 carry row, marked carried (no fresh adjudication in an unattended cut)
python3 -I - <<PY
import csv
r=list(csv.DictReader(open("$B/cut0900/carry.tsv"),delimiter="\t"))
for x in r: x["carried"]="1"
w=csv.DictWriter(open("carry.tsv","w",newline=""),fieldnames=["die","class_id","count","basis","source","owner","carried"],delimiter="\t",lineterminator="\n"); w.writeheader(); w.writerows(r)
PY
mkdir -p stage; cp $C/lanes/CLASSES.tsv $C/lanes/CLASS-MAP.tsv $C/lanes/CLASS-TREND.tsv stage/
python3 -I $T/class_track.py cut --label "$LABEL" --pre-dir pre --carry carry.tsv --meta $B/cut0900/meta.tsv --plans plans.tsv --trend stage/CLASS-TREND.tsv --classes stage/CLASSES.tsv --write > cut.out 2>&1
cat cut.out
[ "$DRY" = dry ] && exit 0
cp stage/CLASSES.tsv stage/CLASS-TREND.tsv $C/lanes/
cd $C && bash bin/coord-commit.sh "CLASS-TRACK $LABEL cut: CLASSES + CLASS-TREND" lanes/CLASSES.tsv lanes/CLASS-TREND.tsv 2>&1 | tail -1
bash bin/post.sh CLASS-TRACK "RESULT [CLASS-TRACK -> COORD] $LABEL cut (automatic: PRE + RSTREACH on live plans; lane-measured and adjudicated rows carried from 09:00 and excluded from the fall test). $(grep -E '^(S81|HEAD|QC|KV|FLEET) ' $D/cut.out | cut -c1-400 | tr '\n' '|')"
if grep -q "^LOOP: [A-Z]" $D/cut.out; then
  bash bin/post.sh CLASS-TRACK "LOOP [CLASS-TRACK -> COORD] $LABEL: two cuts without a fall on $(grep '^LOOP:' $D/cut.out | cut -d' ' -f2-). Per-class breakdown: $(sed -n '/^LOOP-BREAKDOWN/,$p' $D/cut.out | tr '\n' ';' | cut -c1-3000)"
fi
