#!/bin/bash
# TYPE-REDUCE-3/HBM: prepare + launch the per-variant kit LEC (gold = OLD variant kit RTL, gate = strap master netlist
# with the straps tied to the variant's constant).  prep_lec.sh WT OUT MASTER MASTER_KIT MEM_GB [first_last|all|rest]
WT=$1; OUT=$2; M=$3; MK=$4; MEM=$5; SEL=${6:-all}
N=$(ls $MK/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | head -1)
[ -f "$N" ] || { echo "no master netlist in $MK"; exit 3; }
CT=$(python3 -c "import json;print([v for v in json.load(open('$WT/physical/die_plan/hbm_arch_cores/views_b2n_strap.json'))['view_list'] if v['module']=='$M'][0]['strap_master']['canonical_type'])")
python3 - "$WT" "$M" "$SEL" <<'PY' > $OUT/logs/lec_sel_$M.txt
import json,sys
wt,m,sel=sys.argv[1:4]
v=json.load(open(f'{wt}/results/type_reduce3_1025/hbm/variants.json'))[m]
idx=list(range(len(v)))
if sel=='first_last': idx=sorted({0,len(v)-1})
elif sel=='rest': idx=[i for i in idx if i not in (0,len(v)-1)]
for i in idx:
    x=v[i]; print(x['old_view'].replace('@','_'), ','.join(f'{k}={val}' for k,val in x['straps'].items()))
PY
while read OV ST; do
  D=$OUT/lec/$OV; rm -rf $D; mkdir -p $D
  rsync -a --exclude run --exclude lec $OUT/old/$OV/ $D/kit/ || exit 4
  python3 $WT/results/type_reduce3_1025/hbm/mk_variant_gate.py $MK $N $D/kit $CT "$ST" $D/gate.v > $D/mk_gate.json 2> $D/mk_gate.err || { echo "$OV GATE_EDIT_FAIL $(tail -1 $D/mk_gate.err)"; continue; }
  cp $WT/tools/die_plan/lec.py $D/lec.py
  printf '%s\n' "cd $D && python3 -I $D/lec.py $D/kit --netlist $D/gate.v --out $D/lec --mem $MEM --jobs 8 > $D/lec_run.log 2>&1; rc=\$?; tail -2 $D/lec_run.log; exit \$rc" > $D/run.sh
  echo "$OV $ST" > $D/variant.txt
  nohup ~/.local/bin/ot-run --mem $MEM --threads 8 --dir $D -- bash $D/run.sh > $D/otrun.log 2>&1 < /dev/null &
  echo "$OV launched pid $!"; sleep 2
done < $OUT/logs/lec_sel_$M.txt
