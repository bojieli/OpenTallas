#!/usr/bin/env bash
# Fleet replay after building tb_hbm_svg_rel_sm with SMB_SRAMFIFO,SMB_ATTENTION.
# Arguments: immutable compiler source directory, KV fixture root, executable, output root.
# The directory/executable/fixture must be present on the same admitted fleet host.
set -euo pipefail
SRC=$1
KV=$2
EXE=$3
OUT=$4
/home/ubuntu/bin/ot-run --mem 4 --threads 1 --dir "$OUT" -- bash -c '
set -eu
cd "$1"
export HDC_V41_ARITH=chunk8
for trial in kv8 kv4 wrong_row; do
  sm=0
  mutation=""
  if [ "$trial" = kv4 ]; then sm=2; fi
  if [ "$trial" = wrong_row ]; then mutation=wrong_row; fi
  set +e
  python3 tools/hbm_layer_vehicle/attention_prel_svg.py --kv "$2" --layer 2 --sm "$sm" \
    --name "$trial" --work "$4/work" --exe "$3" --out "$4/out/$trial.json" --mut "$mutation" \
    > "$4/out/$trial.log" 2>&1
  rc=$?
  set -e
  echo "$trial RC=$rc"
  if [ "$trial" != wrong_row ] && [ "$rc" -ne 0 ]; then exit "$rc"; fi
  if [ "$trial" = wrong_row ] && [ "$rc" -eq 0 ]; then exit 1; fi
done
' bash "$SRC" "$KV" "$EXE" "$OUT"
