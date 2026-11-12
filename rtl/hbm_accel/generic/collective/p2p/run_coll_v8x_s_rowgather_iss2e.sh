#!/usr/bin/env bash
# HBM-TAPS 11-12 (DO_NOT_COUNT): COLL.ROW_GATHER end-to-end on the q3bc parent ot_hfd_coll_q3_hard_v8x_s (NLINK 3,
# TP 192, VM_RT 81, ROWS 256) with tb_hgi_coll_v8x_s_rowgather (SPMD loopback, q3 only). Verilator 5.050.
#   run_coll_v8x_s_rowgather_iss2e.sh OUT MODE        env R (default 623), W (default 453), CASES override
# MODE ref      : v7 issuer, C=1 programmes (row_gather_rows --vm-rt 81), P1 P6 -> PASS (bench-model positive control)
#      iss2e    : ISS2E + BANK_RQREG + the compiler's union pad / hold masks (manifest issue_pad_mask / issue_hold_mask),
#                 programmes --issue-cadence 2 --arg-start-reg --arg-pr-source: P1 P6 -> PASS,
#                 P3_row_stride P3_link_step (compiler mutants) -> FAIL
#      notaprep : as iss2e with OT_COLL_ISS8E_MUT_NOTAPREP, P6 -> FAIL
#      nopad    : ISS2E without masks, C=2 programme, P6 -> FAIL
#      c1oniss2e: ISS2E with masks, C=1 programme, P6 -> FAIL
# (needs the COMPILER-CAL-3 claude/compiler-cal-iss2e-1112 @f6bd2f7449 tools for --issue-cadence 2)
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd); ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); MODE=${2:?mode}; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
R=${R:-623}; W=${W:-453}; VMRT=81
p=rtl/hbm_accel/generic/collective/p2p; t=rtl/hbm_accel/generic/collective/tkm; M=physical/asap7_memory_macros
src=("$p/tb_hgi_coll_v8x_s_rowgather.sv" "$p/ot_hfd_coll_q3_hard_v8x_s.sv" "$p/ot_hgi_coll_edge_pr.sv" "$p/ot_hfd_coll_q2_hard_v8g_s.sv"
 "$p/ot_hgi_coll_reduce_static_pr.sv"
 "$p/ot_hfd_coll_q_hard_v8g.sv" "$p/ot_hfd_coll_q_hard_v5.sv" "$p/ot_hgi_coll_ctl_v5.sv" "$p/ot_hfd_coll_q3_static_host_v4.sv"
 "$p/ot_hfd_coll_q2_static_host_v4.sv" "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv"
 "$p/ot_hgi_coll_static_issuer.sv" "$p/ot_hgi_coll_static_issuer_v5.sv" "$p/ot_hgi_coll_static_issuer_v6.sv"
 "$p/ot_hgi_coll_static_issuer_v7.sv" "$p/ot_hgi_coll_qslots.sv"
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
 "$M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
 "$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" "$M/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v")
C2=(--issue-cadence 2 --arg-start-reg --arg-pr-source)
python3 tools/hbm_coll_static/row_gather_rows.py "$OUT/rg_mask" --P 1 --R "$R" --wire "$W" --vm-rt $VMRT "${C2[@]}" > "$OUT/rg_mask.log"
read -r PM HM < <(python3 - "$OUT/rg_mask/manifest.json" <<'PY'
import json, sys
def find(d, k):
    if isinstance(d, dict):
        for kk, vv in d.items():
            if kk == k: return vv
            r = find(vv, k)
            if r is not None: return r
m = json.load(open(sys.argv[1])); print(find(m, "issue_pad_mask"), find(m, "issue_hold_mask"))
PY
)
echo "pad $PM" > "$OUT/masks.txt"; echo "hold $HM" >> "$OUT/masks.txt"
B=(+define+OT_COLL_ISSUER256_ISS2E +define+OT_COLL_ISS8E_BANK_RQREG); MK=(+define+OT_COLL_ISS8E_PAD_MASK=$PM +define+OT_COLL_ISS8E_HOLD_MASK=$HM)
E="$p/ot_hgi_coll_issuer_m256v8e.sv"
DEF=(); CA=(); CASES="P6"
case $MODE in
 ref)       CASES="P1 P6";;
 iss2e)     src+=("$E"); DEF=("${B[@]}" "${MK[@]}"); CA=("${C2[@]}"); CASES="P1 P6 P3_row_stride P3_link_step";;
 notaprep)  src+=("$E"); DEF=("${B[@]}" "${MK[@]}" +define+OT_COLL_ISS8E_MUT_NOTAPREP); CA=("${C2[@]}");;
 nopad)     src+=("$E"); DEF=("${B[@]}"); CA=("${C2[@]}");;
 c1oniss2e) src+=("$E"); DEF=("${B[@]}" "${MK[@]}");;
 *) echo "unknown mode $MODE"; exit 2;;
esac
[ -n "${CASES_OVR:-}" ] && CASES=$CASES_OVR
sha256sum "${src[@]}" "$0" tools/hbm_coll_static/row_gather_rows.py tools/hbm_coll_static/iss2e_pad.py "$p/static_uop_layout_v4.json" > "$OUT/sources.sha256"
"$V" --version > "$OUT/verilator.version"; echo "MODE $MODE R $R W $W VM_RT $VMRT" > "$OUT/config.txt"
"$V" --binary --timing -O1 -j "${JOBS:-16}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
 -Wno-TIMESCALEMOD -Wno-INITIALDLY -Wno-MULTITOP -Wno-BLKSEQ -Wno-WIDTHCONCAT --top-module tb_hgi_coll_v8x_s_rowgather \
 -GNLINK=3 -GTP=192 -GVM_RT=$VMRT -GROWS=256 "${DEF[@]}" --Mdir "$OUT/obj" -o tb "${src[@]}" > "$OUT/build.log" 2>&1 \
 || { tail -40 "$OUT/build.log"; echo "ROWGATHER_V8XS build FAIL"; exit 2; }
rc=0
for case in $CASES; do
 P=${case%%_*}; P=${P#P}; mut=${case#P$P}; mut=${mut#_}; c=$OUT/$case
 g=(python3 tools/hbm_coll_static/row_gather_rows.py "$c/prog" --P "$P" --R "$R" --wire "$W" --vm-rt $VMRT "${CA[@]}")
 [ -n "$mut" ] && g+=(--mutant "$mut")
 "${g[@]}" > "$c.compile.log" 2>&1 || { cat "$c.compile.log"; echo "$case: compile FAIL"; rc=1; continue; }
 nr=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['parents']['d0q0']['rows'])" "$c/prog/manifest.json")
 # ROWS 256 metadata: row_gather_rows.py emits the 64-row (issuer v6) loop ids (63 = single visit, loop id = pc); the 256-row
 # issuer v7 has 32 counters by id and faults on an id >= 32 (issuer fault, cause bit 1, while programming).  Same dense
 # first-use rename as argmax_rows.enc_meta at PW 8 (injective: loop semantics and every iteration value unchanged);
 # programmes here are < 64 rows, so next/target bits 54/55 stay 0.  Original kept as d0q0.meta.v6.hex.
 python3 - "$c/prog/d0q0.meta.hex" "$nr" <<'PY'
import sys
f, nr = sys.argv[1], int(sys.argv[2]); L = [l.split()[0] for l in open(f) if l.strip()][:nr]
open(f.replace('.meta.hex', '.meta.v6.hex'), 'w').write('\n'.join(L) + '\n')
ids, out = {}, []
for h in L:
    m = int(h, 16); lid = (m >> 45) & 63
    if (m >> 51) & 0x3f: raise SystemExit('meta bits 51..56 already set: not a v6 row')
    d = ids.setdefault(lid, len(ids))
    if d >= 32: raise SystemExit(f'{len(ids)} loop ids > 32 (issuer v7)')
    out.append('%016x' % ((m & ~(63 << 45)) | (d << 45)))
open(f, 'w').write('\n'.join(out) + '\n'); print(f'META_LID_REMAP {len(ids)} ids')
PY
 set +e; "$OUT/obj/tb" +DIR="$c/prog" +P="$P" +R="$R" +W="$W" +NR="$nr" > "$c.log" 2>&1; set -e
 tail -1 "$c.compile.log"; grep -E '^(ROWGATHER|LANE|DATA_|ADDR_|FAULT)' "$c.log" | head -12
 pos=0; [ "$MODE" = ref ] && pos=1; [ "$MODE" = iss2e ] && [ -z "$mut" ] && pos=1
 if [ $pos = 1 ]; then grep -q '^ROWGATHER_ROWS PASS' "$c.log" || { echo "$case: expected PASS"; rc=1; }
 else if grep -q '^ROWGATHER_ROWS FAIL' "$c.log"; then echo "$case: rejected (expected FAIL)"; else echo "$case: SURVIVED"; rc=1; fi; fi
done
[ -n "${KEEP_OBJ:-}" ] || rm -rf "$OUT/obj"
[ $rc = 0 ] && echo "ROWGATHER_V8XS $MODE GATE PASS" || echo "ROWGATHER_V8XS $MODE GATE FAIL"
exit $rc
