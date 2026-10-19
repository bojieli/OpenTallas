#!/bin/bash
# MU-TOK-KV2 10-19: cut + build + run ONE KV attention vehicle from a KV die GEN run dir, hierarchical Verilator build.
#   kva_vehicle.sh VEH DIE_RUN KSRC OUT CASES
#   VEH   all = the whole attention slice qwk_slice_attn (4 stacks, exact RESULT check, mutants)
#         WS|WN|ES|EN = PER-STACK vehicle qwk_stk_<s>: astk_<s> + its 8 ECTLs + 4 V ports + 32 head units (+ the relays /
#         landings / reset regions grown from them) + the shared control kvs_attn / seq / ahub / pvw / pvfin (timing only)
#   DIE_RUN  kvs14* run dir holding port_bind_v2/{die_bound.v,port_bind_v2.json}, case_kv/relay_stages.json, relay_check.json
#   KSRC     the GEN source tree of that run (wt-kvs14*)
# WSQK/WNQK/ESQK/ENQK isolate a QK strip: PV pair clusters are outside the cut; only K requests and strip partials are judged.
# Env: KVA_HIER (default the head-unit leaf masters + the PV pair cluster qkd_pvw_die_t, 404k station flops each: MU-TOK-KV3) -> run_kv_attn_mu.sh hierarchical blocks; KVA_VFLAGS, KVA_J.
set -u
VEH=$1; QK=0
case "$VEH" in WSQK|WNQK|ESQK|ENQK) VEH=${VEH%QK}; QK=1;; esac
#   KV-TOK 10-19 (MU dies only): P0 | P1 = PV PAIR vehicle qwk_pv_P<p>: the pair's two stacks + PV pair cluster pvw_<p>
R=$2; K=$3; OUT=$(mkdir -p "$4" && readlink -f "$4"); CASES=$(readlink -f "$5")
H=$(cd "$(dirname "$0")" && pwd)
SH='qkd_kvs_attn|qkd_seq_static_s|qkd_ahub_static_dw|qkd_pv_fin_s'
[ "$QK" = 1 ] || SH="$SH|qkd_pvw_die_t"
# KV-TOK 10-19: MU KV dies (kvs14r GEN2+, OT_KV_MU=1) are FLATTENED: the strip is astk_<s>__* (qkd_astk_ctl_s/ep_s/ex_s/
# zn/er_owner_st/fault_join/rly_296_fl), the sequencer seq__* (core/fan/xs), and each PV pair cluster pvw_<p>__* (256 pv
# slices, 32 joins, wide ctl, rs head, rlyi + 2.5k relay stations at die level).  Selection is then by instance prefix;
# the PV pairs come in as die instances (per-pair leaves become hier blocks: KVA_HIER default below), not one 7.7 MB module.
MU=0; grep -q '"qkd_astk_ctl_s"' $R/port_bind_v2/port_bind_v2.json && MU=1
if [ "$MU" = 1 ]; then
  SHI='kvs_attn|ahub|pvfin|seq__.*'; [ "$QK" = 1 ] || SHI="$SHI|pvw_\d+__.*"
  if [ "$VEH" = P0 ] || [ "$VEH" = P1 ]; then
    # PV PAIR vehicle: PV pair cluster p is fed by exactly two stacks (pvw_0 <- WS+ES headers, pvw_1 <- WN+EN: the
    # die's pvw_<p>__u_ctl in_valid/in_t), so a one-stack cut leaves half its V headers undriven and PV never completes.
    # The pair vehicle = its two stacks (strip, 16 ECTLs, 8 V ports, 64 heads) + its own pair (other pair outside) + shared
    # control.  RESULT (pvfin joins both pairs) stays partial; judged: K/V requests, partials, pair out/rs, pvfin beat 0.
    p=${VEH#P}; [ $p = 0 ] && S2='WS|ES' && STK=WS,ES || { S2='WN|EN'; STK=WN,EN; }
    TOP=qwk_pv_$VEH; SEL=(--inst "kvs_attn|ahub|pvfin|seq__.*|pvw_${p}__.*|astk_($S2)__.*|ectl_($S2)_\d+|vport_($S2)_\d+|head_($S2)_.*")
  elif [ "$VEH" = all ]; then
    TOP=qwk_slice_attn; SEL=(--inst "$SHI|astk_(WS|WN|ES|EN)__.*|ectl_(WS|WN|ES|EN)_\d+|vport_(WS|WN|ES|EN)_\d+|head_(WS|WN|ES|EN)_.*"); STK=WS,WN,ES,EN
  else
    TOP=qwk_stk_$VEH; SEL=(--inst "$SHI|astk_${VEH}__.*|ectl_${VEH}_\d+|vport_${VEH}_\d+|head_${VEH}_.*"); STK=$VEH
  fi
  HDEF='ot_qkh_.*|qkh_head_.*|ot_qwen_tp8_pv_slice_t|ot_qwen_tp8_pv_join_t|qkd_rlyi_.*|qkd_astk_ex_s|qkd_astk_ep_s|qkd_rlys.*|qkd_rlysh.*|qkd_landsh.*|qkd_astk_rly_.*'
elif [ "$VEH" = all ]; then
  TOP=qwk_slice_attn; SEL=(--master "$SH|qkd_astk_strip_er_die|qkd_ectl3_kiss_st|qkd_pv16_vport|ot_qkh_.*|qkh_head_.*"); STK=WS,WN,ES,EN
  HDEF='ot_qkh_.*|qkh_head_.*|qkd_pvw_die_t'
else
  TOP=qwk_stk_$VEH; SEL=(--master "$SH" --inst "astk_$VEH|ectl_${VEH}_\d+|vport_${VEH}_\d+|head_${VEH}_.*"); STK=$VEH
  HDEF='ot_qkh_.*|qkh_head_.*|qkd_pvw_die_t'
fi
SL=$OUT/cut
python3 $H/slice_cut.py --die-v $R/port_bind_v2/die_bound.v --bind $R/port_bind_v2/port_bind_v2.json --src $K "${SEL[@]}" \
  --grow 'qkd_rlys.*|qkd_landsh.*|qkd_rst_region.*' --top $TOP --out $SL > $OUT/cut.log 2>&1 || { echo "KVA_CUT_FAIL $VEH"; tail -5 $OUT/cut.log; exit 2; }
python3 $H/kv_attn_grp_map.py --die-v $R/port_bind_v2/die_bound.v --slice $SL/slice.json --relay-stages $R/case_kv/relay_stages.json \
  --out $SL/kva_grp_map.svh --facts $SL/kva_grp_facts.json --stacks $STK >> $OUT/cut.log 2>&1 || { echo "KVA_MAP_FAIL $VEH"; tail -5 $OUT/cut.log; exit 2; }
python3 $H/kva_mu_ports.py --slice $SL/slice.json --relay-stages $R/case_kv/relay_stages.json --relay-check $R/relay_check.json \
  --out $SL/kva_ports.svh >> $OUT/cut.log 2>&1 || { echo "KVA_PORTS_FAIL $VEH"; tail -5 $OUT/cut.log; exit 2; }
tail -3 $OUT/cut.log
[ -n "${KVA_CUT_ONLY:-}" ] && { echo "KVA_CUT_ONLY $VEH MU=$MU"; exit 0; }
KVA_QK_ONLY=$QK KVA_HIER="${KVA_HIER-$HDEF}" bash $H/run_kv_attn_mu.sh $SL $OUT/run $K $CASES
