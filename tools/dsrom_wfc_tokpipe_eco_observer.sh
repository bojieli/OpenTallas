#!/bin/bash
# Same immutable routed objects, original WFC scope union, read-only observer.
set -euo pipefail
TOK_ORIGINAL_RUN=$1
TOK_OBSERVER_OUT=$2
TOK_OBSERVER_PACKAGE=$3
mkdir "$TOK_OBSERVER_OUT"
mkdir -p "$TOK_OBSERVER_OUT/src/tools/w18" "$TOK_OBSERVER_OUT/src/physical/dsrom_wfc_tokpipe/eco_scope" "$TOK_OBSERVER_OUT/orfs/results/asap7/wfc_stg_route/base"
cp "$TOK_ORIGINAL_RUN/src/tools/w18/corner_sta.py" "$TOK_OBSERVER_OUT/src/tools/w18/"
cp "$TOK_OBSERVER_PACKAGE"/*.sdc "$TOK_OBSERVER_OUT/src/physical/dsrom_wfc_tokpipe/eco_scope/"
for f in 6_final.odb 6_final.spef 6_final.sdc; do
 cp "$TOK_ORIGINAL_RUN/route/results/asap7/wfc_stg_route/base/$f" "$TOK_OBSERVER_OUT/orfs/results/asap7/wfc_stg_route/base/"
done
sha256sum "$TOK_OBSERVER_OUT/orfs/results/asap7/wfc_stg_route/base/"6_final.* "$TOK_OBSERVER_OUT/src/physical/dsrom_wfc_tokpipe/eco_scope/"*.sdc > "$TOK_OBSERVER_OUT/objects.sha256"
/usr/bin/time -v -o "$TOK_OBSERVER_OUT/time.txt" python3 "$TOK_OBSERVER_OUT/src/tools/w18/corner_sta.py" --orfs-dir "$TOK_OBSERVER_OUT/orfs" --post-sdc physical/dsrom_wfc_tokpipe/eco_scope/region_die150_union.sdc --output "$TOK_OBSERVER_OUT/corner_sta.json" > "$TOK_OBSERVER_OUT/run.log" 2>&1
python3 - "$TOK_OBSERVER_OUT/corner_sta.json" "$TOK_ORIGINAL_RUN/route/wf_sta.json" > "$TOK_OBSERVER_OUT/equivalence.json" <<'PYVERIFY'
import json,sys
a=json.load(open(sys.argv[1]));b=json.load(open(sys.argv[2]))['corners']
modes=('incontext','reg2reg','region','die150')
tt=min(b['TT'][m]['setup_wns_ps'] for m in modes)
ff=min(b['FF'][m]['hold_wns_ps'] for m in modes)
nt=a['setup_tt']['worst_slack_ps'];nf=a['hold_ff']['worst_slack_ps']
ok=abs(nt-tt)<=0.1 and abs(nf-ff)<=0.1
print(json.dumps(dict(original_tt=tt,original_ff=ff,union_tt=nt,union_ff=nf,rounding_tolerance_ps=0.1,equivalent=ok)))
if not ok:raise SystemExit(1)
PYVERIFY
