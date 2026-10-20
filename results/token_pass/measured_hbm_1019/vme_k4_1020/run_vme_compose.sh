#!/usr/bin/env bash
# run_vme_compose.sh N TAG : census --measured (release row inputs) + vmearly OT_VME_N=N
cd "$(dirname "$0")"; O=results/token_pass/measured_hbm_1019/vme_k4_1020
OT_VME_BLDMA=all OT_VME_N="$1" PYTHONPATH=tools python3 -m hgi_sim.toksim_vme_compose_1020 \
  --measured results/token_pass/measured_hbm_1019/combined_1020/measured_rel_i8_su.json --bw 98 --bridge 1 --out $O/$2.json > $O/$2.log 2>&1
rc=$?; python3 -c "import json,sys;d=json.load(open('$O/$2.json'));r=d['vme_summary']['info_banklat_all'];print('$2', r['ds_ar_tok_s'], r['qwen_tok_s'], json.dumps(r['clients']['ds']['coll']), json.dumps(r['clients']['qwen']['coll']))"
exit $rc
