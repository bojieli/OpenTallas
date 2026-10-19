# QW-KVATTN: history-seeded TP4 ISA golden of P8191 for L0 + L1 with the attention operands kept
set -u
G=/srv/opentallas-scratch/claude/qw-kvattn-1018; T=/srv/opentallas-scratch/claude/tokpass-qwen-1018; FX=$T/fx
export PYTHONPATH=$T/pylib QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 OMP_NUM_THREADS=16 PYTHONDONTWRITEBYTECODE=1
cd $T/src
echo "gold start $(date) src $(cat SOURCE_COMMIT)" > $G/gold.status
/usr/bin/time -f "%e s %M KB" -o $G/gold.time python3 $G/tools/qwen_layerbench/kv_attn_gold.py --src $T/src --out $G/gold -- \
  --run --device cpu --prep-dir $FX/prep/tp4 --layers 2 --tokens $FX/inputs/prompt_tokens_8192.txt --positions 8191 \
  --embedding-npz $FX/inputs/prompt_embedding.npz --kv-history $FX/history_l3 --out $G/gold > $G/gold.log 2>&1
echo "gold rc=$? end $(date)" >> $G/gold.status
