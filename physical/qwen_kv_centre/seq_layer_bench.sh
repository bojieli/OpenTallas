#!/bin/bash
# Qwen ROM TP8 track B: the KV-end attention layer step THROUGH THE MERGED-DIE SEQUENCER, bit-exact against the golden
# (tools/qwen_nearhbm_attn_ref.py vectors), from the source root.  Same vectors, stack (STACK=h) and KV-side stage
# counts as the two-die gate tools/qwen_kv_die/bench_gate.sh (ROM_ST 28, LINK 7, QX 29, RX 28, KVL 34); the link
# (KV_ST, PHY) no longer exists.
# Each run is a whole decode step through the die's stage stepper: host d_start -> 38 stages on the ROM sequencer's raw
# pins (the layer's stage launches the attention by the kvd score descriptor) -> done level with the token.
#   seq_layer_bench.sh pos OUT [flat|cluster]   7 vectors x VM stall 0 / 1 = 14 runs; rc 0 iff all are bit-exact.
#        Prints "PASS qkd_seq_layer <dut> runs=14 exact=14 step_8192=<cycles>" (step = launch descriptor sent -> last
#        RES word at the VM face, 8192_normal, stall 0).
#   seq_layer_bench.sh neg OUT MUT [flat|cluster]   mutant on 8192_normal: rc 0 iff exact (expect FAIL).
#        flat: MUT 2 KV merge off | 5 Q beats swapped | 13 launcher layer + 1 | 15 ROM-sequencer program copy one address up
#        cluster: MUT = wire -> the parent's wiring mutant (OT_QKD_SEQ_MUT)
set -u
MODE=$1; OUT=$2
SRC=$(pwd)
mkdir -p "$OUT/v" "$OUT/log"
G="-GROM_ST=28 -GLINK=7 -GQX=29 -GRX=28 -GKVL=34 ${DQ:+-GDQ=$DQ}"
if [ "$MODE" = pos ]; then
  DUT=${3:-flat}
  for spec in 8192:normal 8192:peaky 8191:mixed 4097:flat 2048:wide 129:tiny 1:normal; do
    c=${spec%%:*}; k=${spec##*:}
    [ -f $OUT/v/${c}_$k/gold.hex ] || python3 tools/qwen_nearhbm_attn_ref.py vectors --ctx $c --seed $((c*7+${#k})) --kind $k --out $OUT/v/${c}_$k > $OUT/log/vec_${c}_$k.log 2>&1 &
  done
  CLUSTER=$( [ "$DUT" = cluster ] && echo 1 ) bash physical/qwen_kv_centre/build_layer_m.sh "$OUT/b0" $G -GMUT=0 > "$OUT/log/build.log" 2>&1 &
  wait
  [ -x "$OUT/b0/Vtb" ] || { echo "BUILD_FAIL: no $OUT/b0/Vtb"; tail -n 5 "$OUT/b0/build.log" 2>/dev/null
    grep -qE "threw signal (9|15)|Killed" "$OUT/b0/build.log" 2>/dev/null && echo "build tool Killed by a signal (memory pressure / earlyoom)"
    exit 3; }
  res=$OUT/results.jsonl; : > $res
  for d in $OUT/v/*/; do
    n=$(basename $d)
    for st in 0 1; do
      r=$($OUT/b0/Vtb $d $st 16 750 400000 0 0 2>$OUT/log/base_${n}_s${st}.err); rc=$?
      echo "{\"run\": \"base\", \"vec\": \"$n\", \"stall\": $st, \"rc\": $rc, \"res\": ${r:-null}}" >> $res
    done
  done
  python3 - "$res" "$DUT" <<'PY'
import json, sys
rows = [json.loads(x) for x in open(sys.argv[1]) if x.strip()]
ex = [r for r in rows if r['rc'] == 0 and r['res'] and r['res']['exact']]
ok = len(rows) == 14 and len(ex) == 14
step = {(r['vec'], r['stall']): r['res']['marks']['res_last_at_vm'] - r['res']['marks']['ctl_sent'] for r in rows if r['res']}
print(json.dumps(dict(runs=len(rows), exact=len(ex), step={'%s s%d' % k: v for k, v in sorted(step.items())})))
print('%s qkd_seq_layer %s runs=%d exact=%d step_8192=%s' % ('PASS' if ok else 'FAIL', sys.argv[2], len(rows), len(ex), step.get(('8192_normal', 0))))
sys.exit(0 if ok else 1)
PY
  exit $?
fi
MUT=${3:-5}; DUT=${4:-flat}
V=$OUT/v/8192_normal
python3 tools/qwen_nearhbm_attn_ref.py vectors --ctx 8192 --seed $((8192*7+6)) --kind normal --out "$V" > "$OUT/log/vec.log" 2>&1 || exit 3
if [ "$DUT" = cluster ]; then
  CLUSTER=1 SEQMUT=1 bash physical/qwen_kv_centre/build_layer_m.sh "$OUT/bm" $G -GMUT=0 > "$OUT/log/build.log" 2>&1 || { tail -5 "$OUT/bm/build.log"; exit 3; }
else
  bash physical/qwen_kv_centre/build_layer_m.sh "$OUT/bm" $G -GMUT=$MUT > "$OUT/log/build.log" 2>&1 || { tail -5 "$OUT/bm/build.log"; exit 3; }
fi
ok=1
r=$("$OUT/bm/Vtb" "$V" 0 16 750 400000 0 0 2> "$OUT/log/mut.err"); rc=$?
echo "{\"run\": \"mut$MUT\", \"dut\": \"$DUT\", \"rc\": $rc, \"res\": ${r:-null}}" | tee -a "$OUT/mut.jsonl"
[ $rc = 0 ] || ok=0
if [ $ok = 1 ]; then echo "PASS qkd_seq_layer $DUT mutant $MUT NOT detected"; exit 0; fi
echo "FAIL qkd_seq_layer $DUT mutant $MUT detected"; exit 1
