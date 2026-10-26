#!/usr/bin/env bash
# P-row COLL.ROW_GATHER on the actual die-bound V4 quadrants (q3 SW host_v4 + q2 host_v4, two dies, real peers).
# NE=2 (default): ONE die {q3, q2}, SPMD loopback of each parent's own TX pin (see the tb header); NE=4: two dies.
# One Verilator build; every case reprograms the same binary through the native HOST target.
#   HCOLL_ROOT=<checkout> bash run_q_static_host_v4_rows_bench.sh OUT [R] [W]
# Cases: ROW_GATHER P1, P6 (PASS); P6 row-stride-dropped, P6 link-slot-step-dropped (must FAIL);
#        ARGMAX_MERGE (q3 ARG fold) A1, A6 (PASS); A6 operand-row-step-dropped (must FAIL). CASES=... selects.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=$(realpath -m "${1:?output directory}");R=${2:-623};W=${3:-453}
mkdir -p "$OUT";cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
p=rtl/hbm_accel/generic/collective/p2p;t=rtl/hbm_accel/generic/collective/tkm
src=("$p/tb_hgi_coll_q_static_host_v4_rows.sv" "$p/ot_hfd_coll_q3_static_host_v4.sv" "$p/ot_hfd_coll_q2_static_host_v4.sv"
 "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv" "$p/ot_hgi_coll_static_issuer.sv"
 "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_reduce_static.sv"
 "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv"
 "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv"
 "$p/ot_hgi_coll_argmax_static.sv" rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv
 "$t/ot_hgi_coll_tkm_static.sv" "$t/ot_hgi_coll_tkm.sv" "$t/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv
 rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
sha256sum "${src[@]}" "$p/run_q_static_host_v4_rows_bench.sh" "$p/static_uop_layout_v4.json" \
 tools/hbm_coll_static/row_gather_rows.py tools/hbm_coll_static/argmax_rows.py > "$OUT/sources.sha256"
"$V" --version > "$OUT/verilator.version"; echo "NE=${NE:-2}" > "$OUT/config.txt"
[[ -n "${REUSE:-}" && -x "$OUT/obj/Vtb_hgi_coll_q_static_host_v4_rows" ]] || "$V" --binary --timing --hierarchical -O1 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
 -GNE="${NE:-2}" --top-module tb_hgi_coll_q_static_host_v4_rows --Mdir "$OUT/obj" "$p/qtkm_hier.vlt" "${src[@]}" > "$OUT/build.log" 2>&1 \
 || { tail -40 "$OUT/build.log";exit 2; }
rc=0
for case in ${CASES:-P1 P6 P6_row_stride P6_link_step A1 A6 A6_vm_step};do
 kind=${case:0:1};P=${case%%_*};P=${P#?};mut=${case#?$P};mut=${mut#_}
 if [[ $kind == P ]];then op=0;tag=ROWGATHER_ROWS
  g=(python3 tools/hbm_coll_static/row_gather_rows.py "$OUT/$case/prog" --P "$P" --R "$R" --wire "$W")
 else op=1;tag=ARGMAX_ROWS
  g=(python3 tools/hbm_coll_static/argmax_rows.py "$OUT/$case/prog" --P "$P")
 fi
 [[ -n "$mut" ]] && g+=(--mutant "$mut")
 "${g[@]}" > "$OUT/$case.compile.log"
 nq3=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['parents']['d0q0']['rows'])" "$OUT/$case/prog/manifest.json")
 nq2=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['parents']['d0q1']['rows'])" "$OUT/$case/prog/manifest.json")
 "$OUT/obj/Vtb_hgi_coll_q_static_host_v4_rows" +DIR="$OUT/$case/prog" +P="$P" +R="$R" +W="$W" +NRQ3="$nq3" +NRQ2="$nq2" +OP="$op" \
   > "$OUT/$case.log" 2>&1 || true
 cat "$OUT/$case.compile.log";grep -E '^(ROWGATHER|ARGMAX|LANE|PARENT|DATA|ADDR|ARG_)' "$OUT/$case.log" | head -40
 if [[ -z "$mut" ]];then
  grep -q "^$tag PASS" "$OUT/$case.log" || { echo "$case: expected PASS";rc=1; }
 else
  if grep -q "^$tag FAIL" "$OUT/$case.log";then echo "$case: mutant rejected (expected FAIL)";
  else echo "$case: MUTANT SURVIVED";rc=1;fi
 fi
done
[[ -n "${KEEP_OBJ:-}" ]] || rm -rf "$OUT/obj"
exit $rc
