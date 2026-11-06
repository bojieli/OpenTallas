#!/bin/bash
cd /fv
G=$(ls /fv/kitgold/*.sv | tr "\n" " "); N=$(ls /fv/kitgate/*.sv | tr "\n" " ")
bash /fv/eqoff.sh ot_hbm_svc_sm_issuer_rel /fv/gold/ot_hbm_svc_sm_issuer_rel.sv /fv/gate/ot_hbm_svc_sm_issuer_rel.sv "-chparam ID_COHORT 1 -chparam XSLOT 1"
bash /fv/eqoff.sh ot_svgr_top_cachecut "$G" "$N" "-chparam ID_COHORT 1 -chparam XSLOT 1 -chparam OPEN_IL 1 -chparam CACHE_RW_SRAM 1"
for m in ot_hbm_svc_sm_issuer_rel ot_svgr_top_cachecut; do echo "== $m"; grep -E "Found [0-9]+ \\\$equiv|proven and|unproven|ERROR|Equivalence successfully" /fv/eq_$m.log | tail -4; done
