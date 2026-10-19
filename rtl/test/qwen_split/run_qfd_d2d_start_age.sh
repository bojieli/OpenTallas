#!/bin/bash
# Current benchmark source + exact SAFE3 RTL root (source hash receipt is authoritative).
set -eu
OUT=$(realpath -m "$1");SRC=$(realpath "${2:-.}");R=$(cd "$(dirname "$0")/../../.." && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT";"$V" --version > "$OUT/verilator.txt";grep -q 5.050 "$OUT/verilator.txt"
python3 - "$R" "$SRC" <<'CHECK'
import sys,json,hashlib
from pathlib import Path
r,s=map(Path,sys.argv[1:]);j=json.loads((r/'results/rtl/sysface_d2d_emb_age_1019/receipt.json').read_text())
for p,h in j['source_hashes'].items():assert hashlib.sha256((s/p).read_bytes()).hexdigest()==h,p
CHECK
F=("$SRC/rtl/lib/ot_rst_pipe.sv" "$SRC/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv" "$SRC/rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv" "$SRC/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$SRC/rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv" "$SRC/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv" "$SRC/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_services.sv" "$SRC/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv" "$SRC/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_ovl.sv" "$SRC/rtl/qwen_split/qfd_kvn_static_transport.sv" "$SRC/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" "$R/rtl/test/qwen_split/tb_qfd_d2d_start_age.sv")
for m in 0 1;do
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD -DOT_MEM_NO_INIT --top-module tb_d2d_start_age -GMUT=$m --Mdir "$OUT/obj_m$m" "${F[@]}" > "$OUT/build_m$m.log" 2>&1
 set +e
 "$OUT/obj_m$m/Vtb_d2d_start_age" > "$OUT/run_m$m.log" 2>&1;rc=$?
 set -e
 cat "$OUT/run_m$m.log"
 if [ "$m" = 0 ];then test "$rc" = 0;grep -q D2DEMBAGE_PASS "$OUT/run_m$m.log";else test "$rc" != 0;grep -q D2DEMBAGE_FAIL "$OUT/run_m$m.log";fi
done
