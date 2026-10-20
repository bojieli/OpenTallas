#!/bin/bash
# QXF-LINK 2026-10-18 (TOKEN-XDIE-QWEN F4): rebuild the PRODUCTION die-sequencer image
# rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh from the compiler, with the die seam stages.
#   d2d_cal_image_production.sh OUTDIR        -> OUTDIR/program/ (calendars, calendar.json, txdp.svh) + OUTDIR/d2d_cal_image.svh
# Inputs (committed): the LAYERBENCH-QWEN compiled token path (tools/qwen_layerbench/layer_compile.py at e016b38e4: the priced
# 36-layer path with the KV-programme window law applied -- L1..L35 attn_kv +X, L0 attn_kv shortened to the implemented
# KV service, TOKEN-XDIE-QWEN F7) and the die seam stages below (bundle ages: dv2f14bn tx_slot / rx_record / x3_slot /
# x3_record landed 2, tx_record direct 0; kvs14c every bundle at its member max, F5 / F6).  The die GEN sets the masters'
# TXDP from the D2D_TXDP_C / D2D_TXDP_K lines of the image.  Run from the repository root.
set -eu
OUT=$1
STAGES=${D2D_DIE_STAGES:-2,2,2,3,2,2/11,11,9,9,9,9,9}   # CODEX 10-19: approved coherent MU pair seam (SU uses the same physical stages)
TP=results/rtl/qwen_layer_tput_1018/compiled_L1/d2d/token_path_compiled.json.gz
# HKV-DIE 10-19: KV attention codec edges read from the instantiated qkd_kvs_attn (.LAND(1) -> 2), never assumed
KV_CODEC=${D2D_KV_CODEC:-$(python3 -c "import sys; sys.path[:0]=['tools/qwen_layerbench','tools','tools/qwen_split']; import layer_compile as C; print(C.kv_codec_edges(open('rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k.sv').read()))")}
MU_ARGS=()
[ "${D2D_MU:-0}" = 1 ] && MU_ARGS+=(--mu)
# KV-DCAL2 10-19 (KV-EMB2): D2D_CTX_HOST_REQ=<measured HOST RESULT->context edges> moves the token-run CONTEXT slot after
# RESULT(n) reaches the KV HOST; D2D_EMB_FILL=<fork + 2 + join last + 1> fails closed on a short fill budget
[ -n "${D2D_CTX_HOST_REQ:-}" ] && MU_ARGS+=(--ctx-host-req "$D2D_CTX_HOST_REQ")
[ -n "${D2D_EMB_FILL:-}" ] && MU_ARGS+=(--emb-fill-edges "$D2D_EMB_FILL")
mkdir -p "$OUT"
gunzip -c "$TP" > "$OUT/token_path_compiled.json"
python3 tools/qwen_split/d2d_link_calendar.py --out "$OUT/program" --txl 6 --phy 5 --profile program --die-stages "$STAGES" --kv-codec "$KV_CODEC" \
  "${MU_ARGS[@]}" --host-stages 0 --link-handoff results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json --pinreg \
  --token-path "$OUT/token_path_compiled.json" > "$OUT/program.log"
python3 tools/qwen_split/d2d_cal_seq_image.py "$OUT/program" "$OUT/d2d_cal_image.svh"
echo "image: $OUT/d2d_cal_image.svh (die stages $STAGES, kv codec $KV_CODEC)"
