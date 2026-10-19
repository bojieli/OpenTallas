set -u
G=/srv/opentallas-scratch/claude/qw-kvattn-1018; FX=/srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/realmem/P8191
KSRC=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14p-fa7fe4ff9
export PYTHONPATH=/srv/opentallas-scratch/claude/tokpass-qwen-1018/pylib PYTHONDONTWRITEBYTECODE=1
cd $G
python3 tools/qwen_layerbench/kv_attn_vectors.py --gold gold --fx $FX --ksrc $KSRC --vec vec --out vectors.json > vec.log 2>&1; echo "vec rc=$?" >> vec.log
for m in shift pos; do python3 tools/qwen_layerbench/kv_attn_vectors.py --gold gold --fx $FX --ksrc $KSRC --mutant $m --vec vec_$m --layers 0 --out vectors_$m.json > vec_$m.log 2>&1; echo "vec_$m rc=$?" >> vec_$m.log; done
