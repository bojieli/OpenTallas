#!/usr/bin/env bash
# H-NETLIST D4F 2026-10-16: q2 host V4 native reduce at NLINK = NL (d4f: 1; default regression: 2).
#   run_q_static_host_v4_reduce_nl_bench.sh OUT NL
# Positive MUT0 must PASS; MUT1 (wrong source), MUT2 (late AR), MUT3 (SU early), MUT4 (absent link lane NL used) and,
# when NL != 2, MUT5 (NL=2 slot encoding) must FAIL ($fatal / no PASS line).  Verilator 5.050 (see the NL=2 runner note).
set -uo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); NL=${2:?NL}; mkdir -p "$OUT"
p=$ROOT/rtl/hbm_accel/generic/collective/p2p
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
src=("$p/tb_hgi_coll_q_static_host_v4_reduce_nl.sv" "$p/ot_hfd_coll_q2_static_host_v4.sv"
   "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv" "$p/ot_hgi_coll_static_issuer.sv"
   "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_pring_captured_static.sv"
   "$p/ot_hgi_coll_pring_static_state_capture.sv" "$p/ot_hgi_coll_reduce_static.sv"
   "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv"
   "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv"
   "$ROOT/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$ROOT/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv"
   "$ROOT/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv" "$ROOT/rtl/hdc/ot_hdc_fastfp.sv"
   "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v")
sha256sum "${src[@]}" > "$OUT/sources.sha256"
muts="0 1 2 3 4"; [ "$NL" != 2 ] && muts="$muts 5"
fail=0
for m in $muts; do
 ( "$vl" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -GMUT=$m -GNL=$NL --top-module tb_hgi_coll_q_static_host_v4_reduce_nl \
   --Mdir "$OUT/obj$m" "${src[@]}" > "$OUT/m$m.compile.log" 2>&1 && "$OUT/obj$m/Vtb_hgi_coll_q_static_host_v4_reduce_nl" > "$OUT/m$m.log" 2>&1; echo $? > "$OUT/m$m.rc" ) &
done
wait
for m in $muts; do
 if grep -q "HCOLL_Q2_HOST_V4_NATIVE_REDUCE_NL$NL PASS" "$OUT/m$m.log" 2>/dev/null; then r=PASS; else r=FAIL; fi
 [ -s "$OUT/obj$m/Vtb_hgi_coll_q_static_host_v4_reduce_nl" ] || { echo "NL$NL MUT$m BUILD_FAIL"; tail -5 "$OUT/m$m.compile.log"; fail=1; continue; }
 why=$(grep -m1 -o 'native[^"]*\|Fatal.*\|protocol.*\|coverage' "$OUT/m$m.log" | head -1)
 echo "NL$NL MUT$m $r ${why}"
 if [ $m = 0 ]; then [ $r = PASS ] || fail=1; else [ $r = FAIL ] || fail=1; fi
done
rm -rf "$OUT"/obj*
[ $fail = 0 ] && echo "HCOLL_REDUCE_NL_GATE PASS NL$NL" || { echo "HCOLL_REDUCE_NL_GATE FAIL NL$NL"; exit 1; }
