#!/bin/bash
# fetch_render.sh NAME HOST RUN [ODB_PREF]
N=$1; H=$2; R=$3; P=${4:-}
L=/tmp/claude-1000/visaudit/tiles/$N; mkdir -p $L
timeout 2400 ssh -n -o ConnectTimeout=15 $H "CLKS=\${CLKS:-clk} bash /tmp/visaudit/dump_one.sh $N $R $P; O=/tmp/visaudit/$N; RB=\$(dirname \$(cat \$O/odb.txt) | sed 's#/results/#/reports/#'); mkdir -p \$O/rep; cp \$RB/*.webp \$RB/5_global_route.rpt \$RB/fp_margin_lint.json \$RB/textbook_lint.json \$O/rep/ 2>/dev/null; tar -C \$O -czf /tmp/visaudit/$N.tgz ." > $L/remote.log 2>&1
scp -q $H:/tmp/visaudit/$N.tgz $L/ && tar -C $L -xzf $L/$N.tgz && rm $L/$N.tgz
cd /tmp/claude-1000/visaudit && python3 - "$L" "$N" <<'PY'
import sys,glob,os
from PIL import Image
L,N=sys.argv[1],sys.argv[2]
for w in glob.glob(L+'/rep/*.webp'):
    im=Image.open(w); im.thumbnail((1400,1400)); im.save(w[:-5]+'.png')
sys.path.insert(0,'/home/ubuntu/wt/visaudit-hbm-1016/tools/ref_tile')
import layout_png as LP
if os.path.exists(L+'/dump.json'):
    LP.render_tile(L+'/dump.json', L+'/img', L+'/cong.rpt' if os.path.exists(L+'/cong.rpt') else None, N)
print('rendered', N, sorted(os.listdir(L+'/img')) if os.path.isdir(L+'/img') else None, sorted(os.listdir(L+'/rep')) if os.path.isdir(L+'/rep') else None)
PY
tail -1 $L/remote.log
