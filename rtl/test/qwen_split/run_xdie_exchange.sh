#!/bin/bash
# TOKEN-XDIE-QWEN 2026-10-18: Qwen compute <-> KV D2D exchange co-sim (tb_xdie_qwen_exchange.sv), Verilator 5.050.
# usage (repository root, on the fleet via ot-run): run_xdie_exchange.sh OUTDIR [CONFIG ...]   (default: every config)
# Each config: compile its calendar (tools/qwen_split/xdie_exchange_cal.py), build, run; one line per config:
#   <name> expect=<PASS|FAIL> got=<PASS|FAIL> -> OK | UNEXPECTED
# Exit 0 only when every config met its expectation.  Logs: OUTDIR/<name>/{cal/,build.log,run.log}.
set -u
OUT=$1; shift
R=$(pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/d2d_static_20261015; S=rtl/qwen_sys/split_20261014; Q=rtl/qwen_split
NET_C='2,0,2,2,0,2'            # dv2f14bn as netlisted: tx_slot / rx_payload / kv_x3_slot / x3 landed E 2, rx_v + tx_v direct
NET_K='9,11,9,8,9,6,11'        # kvs14c as netlisted: srx 9, rx_payload 11, att_tx slot 9 / kind 8 / beat 9, tx_v 6, tx_payload 11
PLAN='2,2,2,2,2,2/11,11,9,9,9,11,11'   # every bundle equalised to its netlisted maximum (what the die plan must build)
ZERO='0,0,0,0,0,0/0,0,0,0,0,0,0'
# QXF-SEAMK 10-18 (F6): kvs14c after the generator's bundle pads (tools/qwen_kv_die/kv_bundle_eq.py: srx +2, kind +1, tx_v +5)
# and the OT_KV_ATTN_AT_D2D placement (kvs_attn against the D2D end: rx 0/0, tx slot 1/1/1, tx 0/0, pin geometry of kvs14c)
BEQ_K='11,11,9,9,9,11,11'
AT_D2D_K='0,0,1,1,1,0,0'   
# name | expect | calendar flags | bench -G flags | masters (txdp = compiled TXDP, orig = as-built hard-wired TXDP)
CONFIGS=(
 "vc|PASS|--c-real 1 --k-real 0 --qgap 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=0 -GQGAP=1|txdp"
 "vk|PASS|--c-real 0 --k-real 1 --qgap 0 --stages $PLAN|-GC_REAL=0 -GK_REAL=1 -GQGAP=0|txdp"
 "vc_phy9|PASS|--c-real 1 --k-real 0 --qgap 1 --phy 9 --stages $PLAN|-GC_REAL=1 -GK_REAL=0 -GQGAP=1|txdp"
 "vk_phy9|PASS|--c-real 0 --k-real 1 --qgap 0 --phy 9 --stages $PLAN|-GC_REAL=0 -GK_REAL=1 -GQGAP=0|txdp"
 "vc_abut|PASS|--c-real 1 --k-real 0 --qgap 1 --stages $ZERO|-GC_REAL=1 -GK_REAL=0 -GQGAP=1|txdp"
 "vk_abut|PASS|--c-real 0 --k-real 1 --qgap 0 --stages $ZERO|-GC_REAL=0 -GK_REAL=1 -GQGAP=0|txdp"
 "full_gap1|FAIL|--c-real 1 --k-real 1 --qgap 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GQGAP=1|txdp"
 "full_gap0|FAIL|--c-real 1 --k-real 1 --qgap 0 --stages $PLAN|-GC_REAL=1 -GK_REAL=1 -GQGAP=0|txdp"
 "face_asbuilt|FAIL|--c-real 0 --k-real 2 --qgap 0 --stages $PLAN|-GC_REAL=0 -GK_REAL=2 -GQGAP=0|txdp"
 "masters_asbuilt|FAIL|--c-real 1 --k-real 0 --qgap 1 --stages $ZERO --txd-override 1,1,1,2 --no-extend|-GC_REAL=1 -GK_REAL=0 -GQGAP=1|orig"
 "netlist_c|FAIL|--c-real 1 --k-real 0 --qgap 1 --stages $NET_C/0,0,0,0,0,0,0|-GC_REAL=1 -GK_REAL=0 -GQGAP=1|txdp"
 "netlist_k|FAIL|--c-real 0 --k-real 1 --qgap 0 --stages 0,0,0,0,0,0/$NET_K|-GC_REAL=0 -GK_REAL=1 -GQGAP=0|txdp"
 "netlist_k_beq|PASS|--c-real 0 --k-real 1 --qgap 0 --stages 0,0,0,0,0,0/$BEQ_K|-GC_REAL=0 -GK_REAL=1 -GQGAP=0|txdp"
 "vk_attn_d2d|PASS|--c-real 0 --k-real 1 --qgap 0 --stages 2,2,2,2,2,2/$AT_D2D_K|-GC_REAL=0 -GK_REAL=1 -GQGAP=0|txdp"
 "mut_attn_d2d_torn|FAIL|--c-real 0 --k-real 1 --qgap 0 --stages 2,2,2,2,2,2/0,1,1,1,1,0,0|-GC_REAL=0 -GK_REAL=1 -GQGAP=0|txdp"
 "mut1_kv_run_late|FAIL|--c-real 0 --k-real 1 --qgap 0 --stages $PLAN|-GC_REAL=0 -GK_REAL=1 -GQGAP=0 -GMUT=1|txdp"
 "mut2_phy_bit|FAIL|--c-real 1 --k-real 0 --qgap 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=0 -GQGAP=1 -GMUT=2|txdp"
 "mut3_result_word|FAIL|--c-real 1 --k-real 0 --qgap 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=0 -GQGAP=1 -GMUT=3|txdp"
 "mut4_qslot_late|FAIL|--c-real 1 --k-real 0 --qgap 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=0 -GQGAP=1 -GMUT=4|txdp"
 "mut5_kv_status_zero|FAIL|--c-real 1 --k-real 0 --qgap 1 --stages $PLAN|-GC_REAL=1 -GK_REAL=0 -GQGAP=1 -GMUT=5|txdp"
)
SRC_COMMON=("rtl/lib/ot_rst_pipe.sv" "$S/ot_qwen_crc_parallel.sv" "$S/ot_qwen_static_slot_link.sv" "$S/ot_qkvd_d2d_llr.sv"
 "$S/qkd_native_attention_record.sv" "$D/ot_qwen_d2d_static.sv" "$D/ot_qwen_d2d_services.sv" "$Q/qfd_kvn_static_transport.sv"
 "physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv"
 "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$Q/qfd_native59_dv_service.sv" "$Q/qfd_native59_q_export_control.sv" "$Q/qfd_native59_command_context.sv"
 "$Q/qfd_native59_static_service.sv" "$Q/qfd_native59_record_endpoint.sv" "rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv"
 "$S/qkd_native_attention_programme.sv" "$S/qkd_native59_descriptor_producer.sv" "$S/qkd_native_attention_static_ctl.sv"
 "$S/qkd_native59_command_guard.sv" "$S/qkd_attn_cal_gen.sv" "$S/qkd_attn_service_root.sv" "$S/qkd_attn_result_face_s.sv"
 "rtl/test/qwen_split/xdie_kvs14c/qkd_kvs_attn_kvs14c.sv" "rtl/test/qwen_split/tb_xdie_qwen_exchange.sv")
mkdir -p "$OUT"
sha256sum "${SRC_COMMON[@]}" "$D/ot_qwen_d2d_dies.sv" tools/qwen_split/xdie_exchange_cal.py tools/qwen_split/d2d_link_calendar.py "$0" > "$OUT/source.sha256"
want=("$@")
one() {
  local name=$1 exp=$2 calf=$3 gf=$4 mast=$5 o=$OUT/$1
  mkdir -p "$o"
  python3 tools/qwen_split/xdie_exchange_cal.py --out "$o/cal" $calf > "$o/cal.log" 2>&1 || { echo "$name expect=$exp got=CAL_FAIL -> $([ $exp = FAIL ] && echo OK || echo UNEXPECTED)"; tail -3 "$o/cal.log"; return; }
  local dies="$D/ot_qwen_d2d_dies.sv"
  if [ "$mast" = txdp ]; then
    python3 - "$o/cal/calendar.json" "$D/ot_qwen_d2d_dies.sv" "$o/ot_qwen_d2d_dies_txdp.sv" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))['txd']; t = open(sys.argv[2]).read()
f = lambda v: '{' + ', '.join(f"8'd{x}" for x in reversed(v)) + '}'   # byte p = port p
old_c, old_k = "{8'd4, 8'd1, 8'd3, 8'd3}", "{8'd3, 8'd3, 8'd4, 8'd3}"
assert t.count(f'.TXDP(PR ? {old_c}') == 1 and t.count(f'.TXDP(PR ? {old_k}') == 1
t = t.replace(f'.TXDP(PR ? {old_c}', f'.TXDP(PR ? {f(c["C"])}').replace(f'.TXDP(PR ? {old_k}', f'.TXDP(PR ? {f(c["K"])}')
open(sys.argv[3], 'w').write('// GENERATED by run_xdie_exchange.sh: ot_qwen_d2d_dies.sv with the compiled per-port TXDP (C %s, K %s)\n' % (c['C'], c['K']) + t)
PY
    dies="$o/ot_qwen_d2d_dies_txdp.sv"
  fi
  $V --binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH \
     -DOT_MEM_NO_INIT -I"$o/cal" --top-module tb_xdie_qwen_exchange $gf -GCALDIR="\"$o/cal\"" --Mdir "$o/obj" \
     "${SRC_COMMON[@]}" "$dies" > "$o/build.log" 2>&1 || { echo "$name expect=$exp got=BUILD_FAIL -> UNEXPECTED"; grep -m6 '%Error' "$o/build.log"; return; }
  "$o/obj/Vtb_xdie_qwen_exchange" > "$o/run.log" 2>&1
  rm -rf "$o/obj"
  local got=FAIL; grep -q '^XQ_PASS' "$o/run.log" && got=PASS
  echo "$name expect=$exp got=$got -> $([ $got = $exp ] && echo OK || echo UNEXPECTED)"
  grep -E '^XQ_(E|CFG|PASS|FAIL|CAUSE)' "$o/run.log" | sed 's/^/    /'
  grep -m3 '^XQ_ERR' "$o/run.log" | sed 's/^/    /'
}
pids=()
for c in "${CONFIGS[@]}"; do
  IFS='|' read -r name exp calf gf mast <<< "$c"
  if [ ${#want[@]} -gt 0 ] && ! printf '%s\n' "${want[@]}" | grep -qx "$name"; then continue; fi
  one "$name" "$exp" "$calf" "$gf" "$mast" > "$OUT/$name.summary" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait $p; done
cat "$OUT"/*.summary | tee "$OUT/SUMMARY.txt"
! grep -q 'UNEXPECTED\|BUILD_FAIL' "$OUT/SUMMARY.txt"
