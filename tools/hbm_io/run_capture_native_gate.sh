#!/usr/bin/env bash
set -euo pipefail
root=${HCOLL_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
out=$(realpath -m "$1");mkdir -p "$out"
build=$(mktemp -d /tmp/hcoll-native-transport.XXXXXX)
trap 'rm -rf "$build"' EXIT
cd "$root"
for p in rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v;do
 if git cat-file -e "4c66b6a95:$p" 2>/dev/null;then
  git show "4c66b6a95:$p" > "$build/$(basename "$p")"
 else
  cp "$p" "$build/$(basename "$p")"
 fi
 python3 - "$p" "$build/$(basename "$p")" <<'PYVERIFY'
import json,subprocess,sys
path,copy=sys.argv[1:]
want=json.load(open('rtl/hbm_accel/generic/collective/p2p/static_link_sources.json'))['git_blobs'][path]
have=subprocess.check_output(['git','hash-object',copy],text=True).strip()
assert have==want,(path,have,want)
PYVERIFY
done
p=rtl/hbm_accel/generic/collective/p2p
io=rtl/hbm_accel/io_static_20261015
for m in ${MUTANTS:-0 1 2 3 4 5 6 7 8 9 10 11};do
 iverilog -g2012 -s tb_hgi_coll_static_link_capture -Ptb_hgi_coll_static_link_capture.MUT="$m" -o "$build/sim$m" \
 "$build"/*.sv "$build"/*.v "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv" "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv" \
 "$io/ot_hbm_static_gearbox.sv" "$io/ot_hbm_static_frame_transport.sv" "$p/tb_hgi_coll_static_link_capture.sv"
 vvp "$build/sim$m" > "$out/m$m.log" 2>&1
 cat "$out/m$m.log"
 if [[ "$m" == 0 ]];then
  grep -q 'HBM_STATIC_LINK_CAPTURE_PASS FW545 CW32 checks2048 TX6 RX2 PHY96' "$out/m$m.log"
 elif [[ "$m" == 3 ]];then
  grep -Eq 'HBM_STATIC_LINK_CAPTURE_FAIL.*errors[1-9]' "$out/m$m.log"
 else
  grep -Eq 'HBM_STATIC_LINK_CAPTURE_FAIL.*abort_cycles[1-9]' "$out/m$m.log"
 fi
done
