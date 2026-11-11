#!/bin/bash
# CPL-S81-SLICE SLICE-C re-run under the DS85-COMPOSE legality gate (cgate), on 99f + the LP-W window
cd /srv/opentallas-scratch3/claude/cpl-s81-slice
[ -s plan_99f_win.json ] || python3 -I winshift.py plan_99f.json plan_99f_win.json > winshift_99f.log
mkdir -p srch_g fin_g png_g intent_g
T="dsdv_slice_c1x_C__t1 dsdv_slice_c1x_C__t3 dsdv_slice_c1x_C__t4 dsdv_slice_c1x_C__t6 dsdv_slice_c1x_C__t7 dsdv_slice_c1x_C__t8 dsdv_slice_c1x_C__t9 dsdv_slice_c3x_C__t1 dsdv_slice_iq_C__t1 dsdv_slice_kv512_C__t1 dsdv_slice_lepe_mu_C__t1 dsdv_slice_lepw_mus_C__t1"
printf "%s\n" $T | CGATE_TAPS=0 xargs -P 8 -I{} sh -c "nice -n 19 python3 search.py plan_99f_win.json {} srch_g/{}.json --iters ${ITERS:-3000} --intent --cgate > srch_g/{}.log 2>&1"
echo SEARCH_DONE $(date)
printf "%s\n" $T | xargs -P 6 -I{} sh -c "CGATE=1 INTENT=1 SRCH=srch_g FIN=fin_g PNG=png_g nice -n 19 python3 finalize.py plan_99f_win.json {} > fin_g/{}.log 2>&1"
echo FIN_DONE $(date)
echo ALL_DONE
