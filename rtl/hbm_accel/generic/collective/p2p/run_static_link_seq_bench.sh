#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(git -C "$here" rev-parse --show-toplevel)
build=$(mktemp -d /tmp/hcoll-static-link-seq.XXXXXX)
trap 'rm -rf "$build"' EXIT
# Refuse a current source tree whose native dependencies differ from the proven blobs.
python3 - "$root" "$here/static_link_sources.json" <<'PYVERIFY'
import json,subprocess,sys
root,manifest=sys.argv[1:]
for path,want in json.load(open(manifest))["git_blobs"].items():
    have=subprocess.check_output(["git","-C",root,"rev-parse","HEAD:"+path],text=True).strip()
    if have!=want: raise SystemExit("static link native dependency changed: "+path)
PYVERIFY
# Read exact shared source blobs; never alter Qwen source or substitute memory.
rev=4c66b6a95
paths=(rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv
 rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
 rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
src=()
for p in "${paths[@]}"; do
 out="$build/$(basename "$p")"
 git -C "$root" show "$rev:$p" > "$out"
 src+=("$out")
done
for mutant in ${MUTANTS:-0 1 2 3 4 5 6 7 8 9 10 11}; do
  iverilog -g2012 -s tb_hgi_coll_static_link_seq -Ptb_hgi_coll_static_link_seq.MUT="$mutant" -Ptb_hgi_coll_static_link_seq.N="${FRAMES:-1024}" -o "$build/sim" \
    "${src[@]}" "$here/ot_hgi_coll_static_seq_ctl.sv" "$here/ot_hgi_coll_static_link_seq.sv" "$here/tb_hgi_coll_static_link_seq.sv"
  vvp "$build/sim" > "$build/m$mutant.log" 2>&1
  cat "$build/m$mutant.log"
  if [[ "$mutant" == 0 ]]; then
    rg -q 'HBM_STATIC_LINK_SEQ_PASS FW545 CW32 checks2048 TX3 RX1 PHY96 wire612 sameepoch' "$build/m$mutant.log"
  elif [[ "$mutant" == 3 ]]; then
    rg -q 'HBM_STATIC_LINK_SEQ_FAIL.*errors[1-9]' "$build/m$mutant.log"
    echo "native store mutant $mutant rejected by independent payload scoreboard"
  else
    rg -q 'HBM_STATIC_LINK_SEQ_FAIL.*abort_cycles[1-9]' "$build/m$mutant.log"
    echo "mutant $mutant rejected as required"
  fi
done

iverilog -g2012 -s tb_hgi_coll_static_link_seq_overflow -o "$build/overflow" \
 "${src[@]}" "$here/ot_hgi_coll_static_seq_ctl.sv" "$here/ot_hgi_coll_static_link_seq.sv" "$here/tb_hgi_coll_static_link_seq_overflow.sv"
vvp "$build/overflow"
