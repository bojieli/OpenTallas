#!/bin/bash
# kv-die layer-step bench campaign (remote, detached).
#   bench_run.sh <src> <out> <ROM_ST> <KV_ST> <LINK> <PHY_LAT> <QX> <RX> <KVL> [mutants=1]
# builds base (+ mutants 1-5), generates golden vectors, runs base (stall 0/1) on every vector and each mutant once.
set -u
SRC=$1; OUT=$2; RST=$3; KST=$4; LNK=$5; PL=$6; QX=$7; RX=$8; KVL=$9; MUTS=${10:-1}
mkdir -p $OUT/v $OUT/log
cd $SRC
echo "start $(date) src=$(git -C $SRC log --oneline -1)" > $OUT/STATUS
# vectors
for spec in 8192:normal 8192:peaky 8191:mixed 4097:flat 2048:wide 129:tiny 1:normal; do
  c=${spec%%:*}; k=${spec##*:}
  [ -f $OUT/v/${c}_$k/gold.hex ] || python3 tools/qwen_nearhbm_attn_ref.py vectors --ctx $c --seed $((c*7+${#k})) --kind $k --out $OUT/v/${c}_$k > $OUT/log/vec_${c}_$k.log 2>&1 &
done
# builds: base + mutants
ML="0"; [ "$MUTS" = 1 ] && ML="0 1 2 3 4 5"
for m in $ML; do
  bash rtl/test/qwen_kv_die/build_qkvd_tb.sh $OUT/b$m -GR=8 -GLINK=$LNK -GROM_ST=$RST -GKV_ST=$KST -GPHY_LAT=$PL -GQX=$QX -GRX=$RX -GKVL=$KVL -GMUT=$m > $OUT/log/build$m.log 2>&1 &
done
wait
echo "built $(date)" >> $OUT/STATUS
res=$OUT/results.jsonl; : > $res
for d in $OUT/v/*/; do
  n=$(basename $d)
  for st in 0 1; do
    r=$($OUT/b0/Vtb $d $st 2>$OUT/log/base_${n}_s$st.err); rc=$?
    echo "{\"run\": \"base\", \"vec\": \"$n\", \"rc\": $rc, \"res\": ${r:-null}}" >> $res
  done
done
V=$OUT/v/8192_normal
for m in $ML; do
  [ $m = 0 ] && continue
  st=0; [ $m = 1 -o $m = 4 ] && st=1
  r=$($OUT/b$m/Vtb $V $st 2>$OUT/log/mut${m}.err); rc=$?
  echo "{\"run\": \"mut$m\", \"vec\": \"8192_normal\", \"rc\": $rc, \"res\": ${r:-null}}" >> $res
done
echo "done $(date)" >> $OUT/STATUS
