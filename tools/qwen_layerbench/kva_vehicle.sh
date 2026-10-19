#!/bin/bash
# MU-TOK-KV2 10-19: cut + build + run ONE KV attention vehicle from a KV die GEN run dir, hierarchical Verilator build.
#   kva_vehicle.sh VEH DIE_RUN KSRC OUT CASES
#   VEH   all = the whole attention slice qwk_slice_attn (4 stacks, exact RESULT check, mutants)
#         WS|WN|ES|EN = PER-STACK vehicle qwk_stk_<s>: astk_<s> + its 8 ECTLs + 4 V ports + 32 head units (+ the relays /
#         landings / reset regions grown from them) + the shared control kvs_attn / seq / ahub / pvw / pvfin (timing only)
#   DIE_RUN  kvs14* run dir holding port_bind_v2/{die_bound.v,port_bind_v2.json}, case_kv/relay_stages.json, relay_check.json
#   KSRC     the GEN source tree of that run (wt-kvs14*)
# Env: KVA_HIER (default the head-unit leaf masters) -> run_kv_attn_mu.sh hierarchical blocks; KVA_VFLAGS, KVA_J.
set -u
VEH=$1; R=$2; K=$3; OUT=$(mkdir -p "$4" && readlink -f "$4"); CASES=$(readlink -f "$5")
H=$(cd "$(dirname "$0")" && pwd)
SH='qkd_kvs_attn|qkd_seq_static_s|qkd_ahub_static_dw|qkd_pvw_die_t|qkd_pv_fin_s'
if [ "$VEH" = all ]; then
  TOP=qwk_slice_attn; SEL=(--master "$SH|qkd_astk_strip_er_die|qkd_ectl3_kiss_st|qkd_pv16_vport|ot_qkh_.*|qkh_head_.*"); STK=WS,WN,ES,EN
else
  TOP=qwk_stk_$VEH; SEL=(--master "$SH" --inst "astk_$VEH|ectl_${VEH}_\d+|vport_${VEH}_\d+|head_${VEH}_.*"); STK=$VEH
fi
SL=$OUT/cut
python3 $H/slice_cut.py --die-v $R/port_bind_v2/die_bound.v --bind $R/port_bind_v2/port_bind_v2.json --src $K "${SEL[@]}" \
  --grow 'qkd_rlys.*|qkd_landsh.*|qkd_rst_region.*' --top $TOP --out $SL > $OUT/cut.log 2>&1 || { echo "KVA_CUT_FAIL $VEH"; tail -5 $OUT/cut.log; exit 2; }
python3 $H/kv_attn_grp_map.py --die-v $R/port_bind_v2/die_bound.v --slice $SL/slice.json --relay-stages $R/case_kv/relay_stages.json \
  --out $SL/kva_grp_map.svh --facts $SL/kva_grp_facts.json --stacks $STK >> $OUT/cut.log 2>&1 || { echo "KVA_MAP_FAIL $VEH"; tail -5 $OUT/cut.log; exit 2; }
python3 $H/kva_mu_ports.py --slice $SL/slice.json --relay-stages $R/case_kv/relay_stages.json --relay-check $R/relay_check.json \
  --out $SL/kva_ports.svh >> $OUT/cut.log 2>&1 || { echo "KVA_PORTS_FAIL $VEH"; tail -5 $OUT/cut.log; exit 2; }
tail -3 $OUT/cut.log
KVA_HIER="${KVA_HIER-ot_qkh_.*|qkh_head_.*}" bash $H/run_kv_attn_mu.sh $SL $OUT/run $K $CASES
