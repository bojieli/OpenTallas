#!/bin/bash
# TOK-QK-QCLM r2b 10-27: r2a stage FAILED 7/259 only because stgdie/fx (the stg fixtures) was not staged (252 FileNotFoundError).
# Fixtures = QCL r1 stgdie/fx (intel2 tok-qk-qcl/r1, 324 files). Same fresh-main binary + calibrations; stage only.
set -u
E=/srv/opentallas-scratch2/claude/tok-qk-qclm-r2; T=$E/tree
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH DV2_S8DIE=1 PYTHONDONTWRITEBYTECODE=1
cd $T; export DV_LOWER_VFLAGS="$(cat $E/die/vflags.txt)"
bash $T/tools/qwen_tokfunc/stage_stg_die.sh $E $E/stg_result.json $E/pos_runlist.txt --par ${PAR:-96}
python3 - $E/stgdie/result.json <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));print('QCLM_STG_DIE',r['verdict'],r['matched_pos'],'/',r['cases_total']);raise SystemExit(0 if r['verdict']=='PASS' else 1)
PY
