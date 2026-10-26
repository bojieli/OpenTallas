#!/bin/bash
# kvs_attn_land_pair_bench.sh OUT [BMUT=0] [FMUT=0] [MODES="0 1 ... 14"]: KV-ATTNKIT 10-18 pair lockstep of the registered
# kvs_attn boundary (programme LAND 1 + root / face CAL_PIPE 1) against the as-built chain, rtl/test/kv_bootage_1019/
# tb_kvs_attn_land_pair_ba3.sv, one Verilator build, every mode.  Last line: KVS_LANDPAIR_ALL PASS|FAIL ...; exit 0 only on PASS.
# Run from the repository root on the fleet (ot-run); Verilator = the closure daemon's pinned 5.050.
set -u
O=$1; BM=${2:-0}; FM=${3:-0}; MODES=${4:-"0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15"}
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
rm -rf "$O"; mkdir -p "$O"
S=rtl/qwen_sys/split_20261014
SRC="$S/qkd_native59_descriptor_producer.sv $S/qkd_native59_command_guard.sv $S/qkd_native_attention_record.sv
 $S/qkd_native_attention_static_ctl.sv $S/qkd_native_attention_programme.sv $S/qkd_attn_service_root.sv
 rtl/qwen_sys/kv_bootage_20261019/qkd_native_attention_static_ctl_ba3.sv rtl/qwen_sys/kv_bootage_20261019/qkd_native_attention_programme_ba3.sv $S/qkd_attn_result_face_s.sv rtl/test/kv_bootage_1019/tb_kvs_attn_land_pair_ba3.sv"
verilator --version > "$O/build.log" 2>&1
if ! verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_kvs_attn_land_pair_ba3 \
     -GBMUT=$BM -GFMUT=$FM -Mdir "$O/obj" -o vtb $SRC >> "$O/build.log" 2>&1; then
  if grep -q -i 'pch\|precompiled' "$O/build.log"; then          # one retry on a PCH race (10-18 rule)
    rm -rf "$O/obj"; verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_kvs_attn_land_pair_ba3 \
      -GBMUT=$BM -GFMUT=$FM -Mdir "$O/obj" -o vtb $SRC >> "$O/build.log" 2>&1 || { tail -20 "$O/build.log"; echo "KVS_LANDPAIR_ALL FAIL build bmut=$BM fmut=$FM"; exit 1; }
  else tail -20 "$O/build.log"; echo "KVS_LANDPAIR_ALL FAIL build bmut=$BM fmut=$FM"; exit 1; fi
fi
head -1 "$O/build.log"
np=0; nf=0; tot=0
for m in $MODES; do
  "$O/obj/vtb" +MODE=$m > "$O/mode$m.log" 2>&1
  grep -E '^MISMATCH' "$O/mode$m.log" | head -3
  l=$(grep -E '^KVS_LANDPAIR ' "$O/mode$m.log" | tail -1); echo "${l:-KVS_LANDPAIR FAIL mode=$m no verdict}"
  case "$l" in "KVS_LANDPAIR PASS"*) np=$((np+1)); c=$(echo "$l" | sed -n 's/.*checks=\([0-9]*\).*/\1/p'); tot=$((tot+${c:-0}));; *) nf=$((nf+1));; esac
done
if [ $nf -eq 0 ]; then echo "KVS_LANDPAIR_ALL PASS bmut=$BM fmut=$FM modes=$np checks=$tot"; exit 0; fi
echo "KVS_LANDPAIR_ALL FAIL bmut=$BM fmut=$FM pass=$np fail=$nf checks=$tot"; exit 1
