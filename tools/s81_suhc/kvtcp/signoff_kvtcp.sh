#!/bin/bash
# S81-KVTC-PINS: sign-off of one routed kvtcp run: DRC 0, TT setup >= -42 / FF reg-to-reg hold >= 0 (signoff.sdc,
# corner_sta), routed LEC (gold = the signed kvtch RTL snapshot + the flow's reset-landing wrapper, as lec_rstland_r2.sh),
# export (ref_tile.py export + child_lint), exact M4/M5 OBS (kvpc_exact_m45.py v3), render.
# usage: signoff_kvtcp.sh LABEL KIT
set -euo pipefail
B=/srv/opentallas-scratch2/claude/S81-KVTC-PINS; R=$B/kitrepo; WT=$B/wt; L=$1; K=$2
P=$B/runs/$L; w=$P/work/orfs; o=$B/signoff/$L; mkdir -p $o
odb=$(find $w/results -name 6_final.odb -print -quit); test -s "$odb"
drc=$(find $w/reports -name 5_route_drc.rpt -print -quit); test -f "$drc"
if [ -s "$drc" ]; then echo "DRC_FAIL $(grep -c violation $drc || true)"; exit 4; fi
echo "DRC 0"
cd $B
python3 -I - "$R" "$w" "$K" "$o" <<'PY'
import json,sys
from pathlib import Path
r,w,k,o=sys.argv[1:5]; sys.path.insert(0,r+'/tools/w18')
import corner_sta as C
sdc=f'physical/ref_tile/{k}/signoff.sdc'
import os; os.chdir(r)
tt=C.run(Path(w).resolve(),'tt',[],[sdc]); ff=C.run(Path(w).resolve(),'ff',[],[sdc])
b=next(Path(w,'results').glob('asap7/*/base/6_final.odb'))
d=dict(odb_sha256=C.sha(b),setup=tt,hold=ff)
Path(o,'corners.json').write_text(json.dumps(d,indent=2)+'\n')
s=dict(tt=tt['worst_slack_ps'],ff_r2r=ff['worst_reg_to_reg_slack_ps'],ff_input=ff['worst_input_to_reg_slack_ps'],errors=tt['errors']+ff['errors'])
print('CORNERS',json.dumps(s),flush=True)
assert s['tt']>=-42 and (s['ff_r2r'] is None or s['ff_r2r']>=0), s
PY
# routed LEC
lo=$o/lec; mkdir -p $lo
rel=rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_kvcn.sv; top=dsfd_su_t_kvtc
g=$(find "$w/results" -name ot_rst_land_wrapper.v -print -quit); test -s "$g"
v=$(find "$w/results" -name 6_final.v -print -quit); test -s "$v"
python3 -I - "$R/$rel" "$g" "$lo/top.sv" "$top" <<'PY'
from pathlib import Path
import re,sys
src,wrp,out=map(Path,sys.argv[1:4]); top=sys.argv[4]
wrapper=wrp.read_text()
assert f'module {top} (' in wrapper and f'{top}__ot_pr_core u_ot_pr_core' in wrapper and 'rst__ot_rl1 <= rst__ot_rl0' in wrapper
s,n=re.subn(r'\bmodule\s+'+top+r'\b',f'module {top}__ot_pr_core',src.read_text()); assert n==1
out.write_text(s+'\n'+wrapper)
PY
sha256sum "$R/$rel" "$g" "$lo/top.sv" "$v" > $lo/inputs.sha256
vd=$(dirname "$v")
docker run --rm --memory 40g -e OT_LEC_SLANG_UNROLL_LIMIT=400000 -v "$R:/src:ro" -v "$w:/work:ro" -v "$vd:/net:ro" -v "$lo:/lec" -v "$lo/top.sv:/src/$rel:ro" -w /src openroad/orfs:asap7lock bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 python3 /src/tools/die_plan/lec.py /work --netlist "/net/$1" --out /lec --jobs 6
 rc=$?; chmod -R a+rwX /lec; exit "$rc"' bash "$(basename "$v")" > $lo/driver.log 2>&1 || true
tail -1 $lo/driver.log | cut -c1-300
jq -e '.verdict=="EQUIVALENT"' $lo/lec.json > /dev/null || { echo "LEC_FAIL"; exit 5; }
echo "LEC EQUIVALENT"
# export
eo=$o/export; mkdir -p $eo
sha256sum $odb $o/corners.json $lo/lec.json > $eo/inputs.sha256; echo "kit=$K" >> $eo/inputs.sha256
( cd $R && python3 tools/ref_tile/ref_tile.py export --orfs-dir $w --kit physical/ref_tile/$K --out $eo/views > $eo/export.log 2>&1 ) || true
tail -1 $eo/export.log | cut -c1-260
grep -q "child_lint PASS" $eo/export.log || { echo "EXPORT/CHILD_LINT FAIL"; exit 6; }
# exact M4/M5 abstract
x=$o/exact; mkdir -p $x
printf 'read_db /b/%s\nwrite_abstract_lef -bloat_factor 0 /o/exact_b0.lef\nputs OT_EXACT_DONE\n' "$(basename $odb)" > $x/x.tcl
docker run --rm --memory 24g --user $(id -u):$(id -g) -v $(dirname $odb):/b:ro -v $x:/o openroad/orfs:asap7lock \
  bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /o/x.tcl' > $x/x.log 2>&1
grep -q OT_EXACT_DONE $x/x.log
python3 -I $WT/tools/die_plan/kvpc_exact_m45.py --base $eo/views/dsfd_su_t_kvtc.lef --detail $x/exact_b0.lef --out $x/dsfd_su_t_kvtc.lef --receipt $x/receipt.json
echo "SIGNED_KVTCP $L"
