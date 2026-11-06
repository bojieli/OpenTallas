#!/bin/bash
cd /fv
yosys -q -p "script /fv/match.ys" > /fv/match.log 2>&1; echo "MATCH_COHORT1 rc $?"
yosys -q -p "script /fv/match0.ys" > /fv/match0.log 2>&1; echo "MATCH_COHORT0 rc $?"
bash /fv/eqoff.sh ot_hbm_svc_sm_issuer_rel /fv/gold/ot_hbm_svc_sm_issuer_rel.sv /fv/gate/ot_hbm_svc_sm_issuer_rel.sv "-chparam ID_COHORT 1 -chparam XSLOT 1"
bash /fv/eqoff.sh ot_svgr_cache136_native /fv/gold/ot_svgr_cache136_native.sv /fv/gate/ot_svgr_cache136_native.sv "-chparam PACKED136 1 -chparam RW_SRAM 1"
G=$(ls /fv/kitgold/*.sv | grep -v portlist | tr "\n" " "); N=$(ls /fv/kitgate/*.sv | tr "\n" " ")
bash /fv/eqoff.sh ot_svgr_top_cachecut "$G" "$N" "-chparam ID_COHORT 1 -chparam XSLOT 1 -chparam OPEN_IL 1 -chparam CACHE_RW_SRAM 1"
