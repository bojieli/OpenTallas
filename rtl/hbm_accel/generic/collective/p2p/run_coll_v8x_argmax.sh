#!/usr/bin/env bash
# HBM-ARGMAX (10-19, coordinator HANDOFF 0kj): COLL.ARGMAX_MERGE on the actual d4g SW COLL parent ot_hfd_coll_q3_hard_v8x
# at the d4g VM budget (VM_RT 74) with the 256-row q3 programme memory (ROWS 256, 8-bit pc). Verilator 5.050.
#   run_coll_v8x_argmax.sh OUT MODE        (one bench per MODE; env NLINK/TP select the parent shape, default 2/192 = d4g SW)
# (TP 192: programmes compiled with argmax_rows --start-reg, the argmax_m_tp192 START_REG alignment; TP 96 without.)
# MODE (positives exit 0 on PASS; mutants exit 0 only when EVERY case is rejected with ARGMAX_ROWS FAIL):
#   pass    VM_RT 74, ROWS 256: programmes P1 P2 (straight-line) P3 P6 P16 (peeled modulo loop, 212 rows) -> PASS
#   default VM_RT 0, ROWS 64: the closed-issuer programme (64 rows) on the same parent -> PASS (default path unchanged)
#   full256 VM_RT 96, ROWS 256: a 256-row programme (every row, pc 255) -> PASS
#   r128    VM_RT 32, ROWS 128: a 128-row programme on the 128-row issuer (XDIE-HBM4 / TW2-COLLAR depth) -> PASS
#   pcwrap  MUTANT: issuer pc MSB dropped (OT_COLL_ISS_MUT_PCWRAP; rows >= 128 fetched from row - 128), P6 -> FAIL
#   rowovf  MUTANT: the 212-row programme on a ROWS 128 issuer (row overflow must fault, never wrap), P6 -> FAIL
#   vmrt    MUTANT: programme compiled for VM_RT 73 on the VM_RT 74 parent (one edge short), P6 -> FAIL
#   vmstep  MUTANT: per-position VM operand stride dropped (argmax_rows --mutant vm_step), P6 -> FAIL
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd); ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:?mode}; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
NLINK=${NLINK:-2}; TP=${TP:-192}
SR=(); [ "$TP" = 192 ] && SR=(--start-reg)   # argmax_m_tp192 registers ARG start (START_REG=1): start row one edge earlier
p=rtl/hbm_accel/generic/collective/p2p; t=rtl/hbm_accel/generic/collective/tkm; M=physical/asap7_memory_macros
src=("$p/tb_hgi_coll_v8x_argmax.sv"
 "$p/ot_hfd_coll_q_hard_v8g.sv" "$p/ot_hfd_coll_q_hard_v5.sv" "$p/ot_hgi_coll_ctl_v5.sv" "$p/ot_hfd_coll_q3_static_host_v4.sv"
 "$p/ot_hfd_coll_q2_static_host_v4.sv" "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv"
 "$p/ot_hgi_coll_static_issuer.sv" "$p/ot_hgi_coll_static_issuer_v5.sv" "$p/ot_hgi_coll_static_issuer_v6.sv" "$p/ot_hgi_coll_qslots.sv"
 "$p/ot_hgi_coll_qslots_capture_pin_v2.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_pring_captured_static.sv"
 "$p/ot_hgi_coll_pring_static_state_capture.sv" "$p/ot_hgi_coll_slice_v7.sv" "$p/ot_hgi_coll_reduce_static.sv"
 "$p/ot_hgi_coll_argmax_static.sv" rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv "$p/ot_hgi_coll_static_vmwrite.sv"
 "$p/ot_hgi_coll_static_vmwrite_roots_v6_physical.sv" "$p/ot_hgi_coll_static_vmwrite_roots_v6.sv" "$p/ot_hgi_coll_static_link_capture.sv"
 "$p/ot_hgi_coll_static_capture_ctl.sv" "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv"
 "$p/ot_hgi_coll_static_seq_ctl.sv" "$t/ot_hgi_coll_tkm_static.sv" "$t/ot_hgi_coll_tkm.sv" "$t/ot_hgi_coll_tkm_buffer.sv"
 "$p/ot_hgi_coll_ring_ag.sv" "$p/ot_hgi_coll_ring_ag_lane.sv" "$p/ot_hgi_coll_ariter_tag.sv"
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/lib/ot_rst_relay.sv
 rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv
 "$M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v")
sha256sum "${src[@]}" "$0" tools/hbm_coll_static/argmax_rows.py "$p/static_uop_layout_v4.json" > "$OUT/sources.sha256"
"$V" --version > "$OUT/verilator.version"
VMRT=74; ROWS=256; DEF=(); CASES="6"; CARGS=(); EXPECT=fail
case $MODE in
 pass) CASES="1 2 3 6 16"; EXPECT=pass;;
 default) VMRT=0; ROWS=64; CASES="1 6"; EXPECT=pass;;
 full256) VMRT=96; CASES="6"; EXPECT=pass;;
 r128) VMRT=32; ROWS=128; CASES="6"; EXPECT=pass;;
 pcwrap) DEF=(+define+OT_COLL_ISS_MUT_PCWRAP);;
 rowovf) ROWS=128;;
 vmrt) CARGS=(--vm-rt-override 73);;
 vmstep) CARGS=(--mutant vm_step);;
 *) echo "unknown mode $MODE"; exit 2;;
esac
echo "MODE $MODE NLINK $NLINK TP $TP VM_RT $VMRT ROWS $ROWS expect $EXPECT" | tee "$OUT/config.txt"
"$V" --binary --timing -O1 -j "${JOBS:-16}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
 -Wno-TIMESCALEMOD -Wno-INITIALDLY -Wno-MULTITOP -Wno-BLKSEQ -Wno-WIDTHCONCAT --top-module tb_hgi_coll_v8x_argmax \
 -GNLINK=$NLINK -GTP=$TP -GVM_RT=$VMRT -GROWS=$ROWS "${DEF[@]}" --Mdir "$OUT/obj" -o tb "${src[@]}" > "$OUT/build.log" 2>&1 \
 || { tail -40 "$OUT/build.log"; echo "ARGMAX_V8X build FAIL"; exit 2; }
rc=0
for P in $CASES; do
 c=$OUT/P$P; crows=256; [ "$VMRT" = 0 ] && crows=64; [ "$MODE" = r128 ] && crows=128
 cvm=$VMRT; ca=("${CARGS[@]}")
 if [ "${ca[0]:-}" = --vm-rt-override ]; then cvm=${ca[1]}; ca=(); fi
 python3 tools/hbm_coll_static/argmax_rows.py "$c/prog" --P "$P" --vm-rt "$cvm" --rows "$crows" --npt "$NLINK" "${SR[@]}" "${ca[@]}" > "$c.compile.log" 2>&1 \
  || { cat "$c.compile.log"; echo "ARGMAX_V8X compile P$P FAIL"; rc=1; continue; }
 nr=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['parents']['d0q0']['rows'])" "$c/prog/manifest.json")
 set +e; "$OUT/obj/tb" +DIR="$c/prog" +P="$P" +NR="$nr" > "$c.log" 2>&1; set -e
 cat "$c.compile.log"; grep -E '^(ARGMAX|ARG_|ADDR_|FAULT)' "$c.log" | head -12
 if [ $EXPECT = pass ]; then grep -q '^ARGMAX_ROWS PASS' "$c.log" || { echo "P$P: expected PASS"; rc=1; }
 else
  if grep -q '^ARGMAX_ROWS FAIL' "$c.log" && ! grep -q '^ARGMAX_ROWS PASS' "$c.log"; then echo "P$P: mutant $MODE rejected (expected FAIL)"
  else echo "P$P: MUTANT $MODE SURVIVED"; rc=1; fi
 fi
done
[ -n "${KEEP_OBJ:-}" ] || rm -rf "$OUT/obj"
[ $rc = 0 ] && echo "ARGMAX_V8X $MODE GATE PASS" || echo "ARGMAX_V8X $MODE GATE FAIL"
exit $rc
