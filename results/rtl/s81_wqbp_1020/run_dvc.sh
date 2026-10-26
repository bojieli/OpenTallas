#!/bin/bash
# S81-WQBP 10-20: the die layer-programme compiler (dv_layer_compile.py, TOK.DS.BENCH.1) on L0 / L2 with --fixtures:
# xs_place.lower_placed must emit prog/xs/<attn.wq_b id>.calendar.json + pq_calendar ROM images + is_d from xs_wqb_die
# (pipeline P126 / cfg 52, static checks) for the slice of record.   usage: run_dvc.sh TAG LAYER [extra args]
set -u
D=/srv/opentallas-scratch/claude/s81-wqbp; R=$D/root; B=/srv/opentallas-scratch/claude/toksim-s81d-wqbp; T=$1; L=$2; shift 2
O=$D/out_dvc/$T; [ -e $O ] && { echo REFUSE_EXISTING_OUT; exit 2; }; mkdir -p $(dirname $O); cd $R
timeout 7200 python3 tools/s81_dv/dv_layer_compile.py --layer $L --out $O --die-src /srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref --fixtures $D/fixtures/$L "$@" > $O.log 2>&1
echo "DVC $T rc=$? $(ls $O/prog/xs/ 2>/dev/null | grep -c 'calendar.json') calendar records"; tail -3 $O.log
for c in $O/prog/xs/*.calendar.json; do [ -f $c ] && python3 -c "import json;c=json.load(open('$c'));print('DVC_CAL',c['layer'],c['slice'],c['mode'],c['period'],c['cfg_lead'],'phases',c['nphases'],'ops',c['ops'],'static',c['static']['PASS'],'span',c['predicted_span'])"; done
python3 -c "import json;l=json.load(open('$O/lowering.json'));ops=l.get('ops',l) if isinstance(l,dict) else l;[print('DVC_LOW',x.get('op'),x.get('status'),(x.get('gap') or {}).get('missing','')[:120]) for x in ops if 'wq_b' in str(x.get('op'))]" 2>&1 | head
echo DVC_DONE $T
