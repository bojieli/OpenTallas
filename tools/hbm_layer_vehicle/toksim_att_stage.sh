#!/usr/bin/env bash
# TOKSIM-HBM-att (10-19): stage the CURRENT d4g SM attention master (ot_hbm_accel_smh_attn as bound x16 in
# /home/ubuntu/artifacts/hdie-d4/d4g_gen2e3/pb0/die.v with ENABLE_INT8(1)) as a unit bundle on HOST, plus the KV fixtures.
#   toksim_att_stage.sh RTLREV ROOT DSKV QWKV
# RTLREV  = the die's source rev (claude/hd4g-gen2e3-1019); files = toksim_att_master_files.txt (GEN2b bundle
#           master_files["ot_hbm_accel_smh_attn"] + fc_xr2 + the ENABLE_INT8 converter ot_smh_static_int8 / int8_line).
# DSKV    = host dir of ds_att_kv.py output (L02/...), QWKV = local dir of qwen_att_kv.py output (L0/, chain/).
set -euo pipefail
RTLREV=$1; ROOT=$2; DSKV=$3; QWKV=$4; HOST=${HOST:-ot-epyc6}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=${REPO:-/home/ubuntu/OpenTallas}
SHA=$(git -C "$REPO" rev-parse "$RTLREV")
ssh "$HOST" "mkdir -p $ROOT/bundle $ROOT/kv/ds $ROOT/kv/qwen && rm -rf $ROOT/bundle/*"
git -C "$REPO" archive "$SHA" $(cat "$HERE/toksim_att_master_files.txt") | ssh "$HOST" "tar -x -C $ROOT/bundle"
python3 -c 'import json,sys;print(json.dumps({"ot_hbm_accel_smh_attn":[l.strip() for l in open(sys.argv[1]) if l.strip()]},indent=1))' \
  "$HERE/toksim_att_master_files.txt" | ssh "$HOST" "cat > $ROOT/bundle/master_files.json"
echo "$SHA $RTLREV" | ssh "$HOST" "cat > $ROOT/bundle/RTLREV"
ssh "$HOST" "cp -a $DSKV/. $ROOT/kv/ds/"
tar -C "$QWKV" -c . | ssh "$HOST" "tar -x -C $ROOT/kv/qwen"
ssh "$HOST" "cd $ROOT/bundle && sha256sum rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv && find . -type f | wc -l"
