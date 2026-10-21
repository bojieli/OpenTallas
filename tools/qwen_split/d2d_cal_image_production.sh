#!/bin/bash
# QXF-LINK 2026-10-18 (TOKEN-XDIE-QWEN F4): rebuild the PRODUCTION die-sequencer image
# rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh from the compiler, with the die seam stages.
#   d2d_cal_image_production.sh OUTDIR        -> OUTDIR/program/ (calendars, calendar.json, txdp.svh) + OUTDIR/d2d_cal_image.svh
# Inputs (committed): the LAYERBENCH-QWEN compiled token path (tools/qwen_layerbench/layer_compile.py at e016b38e4: the priced
# 36-layer path with the KV-programme window law applied -- L1..L35 attn_kv +X, L0 attn_kv shortened to the implemented
# KV service, TOKEN-XDIE-QWEN F7) and the die seam stages below (bundle ages: dv2f14bn tx_slot / rx_record / x3_slot /
# x3_record landed 2, tx_record direct 0; kvs14c every bundle at its member max, F5 / F6).  QLB-C4 10-18: QXF-SEAMC lands
# C.tx_record at age 2 (dv2f14bq, SC_TX 2 -> TXD C [8,3,1,9]); the token path is compiled_L1 recompiled on the dv2f14bq
# die-run table (layer_compile.py: attn_kv X 7).  The die GEN sets the masters'
# TXDP from the D2D_TXDP_C / D2D_TXDP_K lines of the image.  Run from the repository root.
# MU-DQ-TXDP 10-19 (COORD 0ki): default = the MU RELEASE PAIR seam, proven by the netlisted-seam pair co-sim (MU-DQ-TOK
# 216852211, xdie_mu_job.sh): compute dv2f18 (record_bundles.py seam-stages on dv2f18mu: tx_slot 2, rx_record 2,
# kv_x3_slot E 2 -> 3, tx_record 2, x3_record 2) / KV kvs14r-mu (BUNDLE_EQ K.rx_record 11, K.tx_slot 9, K.tx_record 9)
# -> TXD C [8,3,1,10] (0x0a010308), K [21,4,3,3] (0x03030415).  D2D_C_DIE_V=<compute die.v> takes the compute part from
# that die as built (record_bundles.py seam-stages, its fwd_lanes.json beside it); D2D_K_STAGES overrides the KV part.
# The strict bind (die_params.py audit (e)) fails a die whose seam differs from the image's recorded stages.
set -eu
OUT=$1
STAGES=${D2D_DIE_STAGES:-2,2,2,3,2,2/11,11,9,9,9,9,9}   # CODEX 10-19: approved coherent MU pair seam (SU uses the same physical stages)
if [ -n "${D2D_C_DIE_V:-}" ]; then
  C=$(python3 tools/qwen_split/record_bundles.py seam-stages "$D2D_C_DIE_V")
  STAGES="$C/${D2D_K_STAGES:-${STAGES#*/}}"
fi
TP=results/rtl/qwen_layer_tput_1018/compiled_L1/d2d/token_path_compiled.json.gz
# HKV-DIE 10-19: KV attention codec edges read from the instantiated qkd_kvs_attn (.LAND(1) -> 2), never assumed
KV_CODEC=${D2D_KV_CODEC:-$(python3 -c "import sys; sys.path[:0]=['tools/qwen_layerbench','tools','tools/qwen_split']; import layer_compile as C; print(C.kv_codec_edges(open('rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k.sv').read()))")}
MU_ARGS=()
[ "${D2D_ROPE:-0}" = 1 ] && MU_ARGS+=(--rope)
[ -n "${D2D_HEAD_PREPARE_EDGES:-}" ] && MU_ARGS+=(--head-prepare-edges "$D2D_HEAD_PREPARE_EDGES")
[ "${D2D_MU:-0}" = 1 ] && MU_ARGS+=(--mu)
# KV-DCAL2 10-19 (KV-EMB2): D2D_CTX_HOST_REQ=<measured HOST RESULT->context edges> moves the token-run CONTEXT slot after
# RESULT(n) reaches the KV HOST; D2D_EMB_FILL=<fork + 2 + join last + 1> fails closed on a short fill budget
[ -n "${D2D_CTX_HOST_REQ:-}" ] && MU_ARGS+=(--ctx-host-req "$D2D_CTX_HOST_REQ")
[ -n "${D2D_EMB_FILL:-}" ] && MU_ARGS+=(--emb-fill-edges "$D2D_EMB_FILL")
# KV-EMBWIN16 10-20: D2D_EMB_WINDOW=<edges> grows the token-run embedding window (L0..L35 + token period move with it)
[ -n "${D2D_EMB_WINDOW:-}" ] && MU_ARGS+=(--emb-window "$D2D_EMB_WINDOW")
# KV-PROG17 10-20: the KV attention r16 tile (OT_KV_ATTN_R16=1: qkd_attn_cal_gen_r16 TX_SHIFT 1, RETIRE_STATIC STATUS_DELAY 213)
# moves the K RESULT burst +D2D_ATTN_TX_SHIFT and the K STATUS +D2D_STATUS_DELAY in every layer (priced in every layer /
# token window); both link ends bind the resulting _r16 image (kv_static_programme LINK_IMAGE, compute sequencer).
[ -n "${D2D_ATTN_TX_SHIFT:-}" ] && MU_ARGS+=(--attn-tx-shift "$D2D_ATTN_TX_SHIFT")
[ -n "${D2D_STATUS_DELAY:-}" ] && MU_ARGS+=(--status-delay "$D2D_STATUS_DELAY")
mkdir -p "$OUT"
gunzip -c "$TP" > "$OUT/token_path_compiled.json"
python3 tools/qwen_split/d2d_link_calendar.py --out "$OUT/program" --txl 6 --phy 5 --profile program --die-stages "$STAGES" --kv-codec "$KV_CODEC" \
  "${MU_ARGS[@]}" --host-stages 0 --link-handoff results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json --pinreg \
  --token-path "$OUT/token_path_compiled.json" > "$OUT/program.log"
python3 tools/qwen_split/d2d_cal_seq_image.py "$OUT/program" "$OUT/d2d_cal_image.svh"
echo "image: $OUT/d2d_cal_image.svh (die stages $STAGES, kv codec $KV_CODEC)"
