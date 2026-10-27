#!/bin/bash
# R17 pipe.sh NAME PLAN R2 [solver args]: sites/identity -> seamfix (dry aid) -> dry exact build -> MC 13+nom TT/FF ->
# collect / pairs / sta-export (plain + RP1 F4G RCX / VMR GRT core views) -> related-pair STA -> HB4 count.  UNCHECKED
P=/srv/opentallas-scratch2/claude/qc-mesh-r17/pkg; W=/srv/opentallas-scratch2/claude/wt/qc-mesh-r17-1027
N=$1; PLAN=$2; R2=$3; shift 3; X="$*"
O=out/$N; cd $P; mkdir -p $O
D="docker run --rm --memory 24g --cpus 2 -e PYTHONPATH=/w/die_plan -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -v $P:/w -v $W/tools/die_plan:/w/die_plan:ro -v $HOME/.cache/opentallas:/root/.cache/opentallas:ro -w /w ot-ngspice:r3"
SA="--r2 $R2 --stage inputs/stage_table.json --lanes vss --islands type --feed periodic --island-edge-sym $X"
cat > $O/dry.sh <<EOS
python3 r17_phys_sites.py $SA --out $O/sites > $O/sites.log 2>&1
python3 r16_seamfix.py $PLAN $O/sites/r15_top_sites.json $O/spec_seamfix.json > $O/seamfix.log 2>&1
python3 -c "import json;s=json.load(open('$O/spec_seamfix.json'));s['exact_reserve']=True;s['channel_hosts']=True;json.dump(s,open('$O/spec_exact.json','w'))"
python3 die_plan/die_clock_mesh.py build $PLAN --explicit-cells $O/spec_exact.json --ndr 16w --out $O/dry_exact > $O/dry_exact.log 2>&1
EOS
$D sh $O/dry.sh &
for C in TT FF; do for S in $(seq 0 13); do
  F=$(printf %s_s%03d $C $S)
  echo "python3 die_plan/qc_clk_mesh3.py solve $SA --no-spine --top-w 16w --top-m 2 --top-reach 450 --thev inputs/thev_r2.json --slew-sens inputs/slew_sens.json --r9-dir r10_inputs --corner $C --sample $S --out $O/$F.json > $O/$F.log 2>&1"
done; done > $O/solve.lst
split -n l/7 -d $O/solve.lst $O/solve_part_
for f in $O/solve_part_0*; do $D sh $f & done
wait
A=die_plan/clk_aocv_table.json
cat > $O/post.sh <<EOS
M="python3 die_plan/qc_clk_mesh3.py"
\$M collect $O/TT_s0*.json --out $O/die_TT.json > $O/collect_TT.log 2>&1
\$M collect $O/FF_s0*.json --out $O/die_FF.json > $O/collect_FF.log 2>&1
MS='{"TT": "$O/die_TT.json", "FF": "$O/die_FF.json"}'
\$M pairs --r2 $R2 --mesh-skew "\$MS" --aocv $A --out $O/pairs > $O/pairs.log 2>&1
\$M sta-export --r2 $R2 --mesh-skew "\$MS" --aocv $A --out $O/sta_in > $O/sta_in.log 2>&1
\$M sta-export --r2 $R2 --mesh-skew "\$MS" --aocv $A --core-view qfd_dv_s8_crh_rp1=231.2,254.4,181.9,203.8 --core-view qfd_dv_s8x_vmr=249.66,263.16,194.06,206.66 --out $O/sta_in_cv > $O/sta_in_cv.log 2>&1
python3 r11_hb_count.py $PLAN $O/pairs/hold_demand_fragment.json $O/hb4_count.json > $O/hb4.log 2>&1
chown -R $(id -u):$(id -g) /w/out
EOS
$D sh $O/post.sh
# related-pair STA runs on the host (die_sta_related drives its own docker characterisation)
for v in sta sta_cv; do src=sta_in; [ $v = sta_cv ] && src=sta_in_cv
  python3 $W/tools/die_plan/die_sta_related.py $P/$O/$src --plan $P/$PLAN --out $P/$O/$v --pair-unc $P/$O/$src/pair_unc.json > $O/$v.log 2>&1; done
echo DONE $N
