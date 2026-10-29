#!/bin/bash
# S81-LP-2: same census method as S81-LP-1 flat_lanebb (Codex parent_sources/syntax_successor/physical_interfaces closure,
# identical synth recipe) for one LP type; BB = space-separated modules to blackbox (exact ports kept) or "none".
set -euo pipefail
top=$1; run=$2; bb=${3:-none}; mem=${4:-48}
S=/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029
B=/srv/opentallas-scratch2/claude/codex-tok-s81-1028/bind_s13rfunc_reset/out
C=/srv/opentallas-scratch2/claude/codex-s81-lp-parent-1029/scripts
mkdir -p "$run"
if [ ! -d "$run/phys" ]; then
  python3 $C/parent_sources.py $S $B $run/census --top $top > $run/sources.out
  python3 $C/syntax_successor.py $run/census $run/syn > $run/syntax.out || { echo "no syntax change"; mkdir -p $run/syn; cp -r $run/census/rtl $run/census/sources.f $run/census/sources.json $run/syn/; }
  python3 $C/physical_interfaces.py $run/syn $run/phys $S > $run/phys.out
fi
b=$run/phys
python3 - "$b" "$bb" <<'PY'
import json,sys
from pathlib import Path
b=Path(sys.argv[1]);bbs=[] if sys.argv[2]=='none' else sys.argv[2].split()
d=json.load(open(b/'sources.json'));names=d['macros'];fs=(b/'sources.f').read_text().splitlines()
physical_sources={v['source'] for v in names.values()}
physical_files={'/out/'+v['snapshot'] for v in d['files'] if v['path'] in physical_sources}
ys=[]
for f in fs: ys.append('read_verilog '+('-lib ' if f in physical_files else '-defer ')+'-sv -DSYNTHESIS '+' '.join('-D'+v for v in d['defines'])+' '+f)
for m in names: ys.append('blackbox '+m)
for k,v in d['params'].items(): ys.append('chparam -set '+k+' '+str(v)+' '+d['top'])
for m in bbs: ys.append('blackbox '+m)
ys+=['hierarchy -check -top '+d['top'],'synth -top '+d['top']+' -flatten','tee -o /out/generic_stat.json stat -json','dfflibmap -liberty /out/lib/seq.lib','abc -D 833 -liberty /out/lib/all.lib','opt_clean','tee -o /out/mapped_stat.json stat -json -liberty /out/lib/all.lib','tee -o /out/mapped_stat.txt stat -liberty /out/lib/all.lib']
(b/('synth_%s.ys'%(sys.argv[2].replace(' ','+') if bbs else 'flat'))).write_text('\n'.join(ys)+'\n')
PY
tag=$( [ "$bb" = none ] && echo flat || echo "${bb// /+}" )
o=$run/out_$tag; mkdir -p $o/rtl; cp $b/rtl/* $o/rtl/; cp $b/synth_$tag.ys $o/synth.ys; cp $b/sources.json $o/
docker run --rm --name "s81lp2-$(basename $run)-$RANDOM" --cpus=8 --memory="${mem}g" --memory-swap="${mem}g" -v "$o":/out -w /out -e HUID="$(id -u)" -e HGID="$(id -g)" openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
mkdir -p /out/lib
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
if [ -f "$L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz" ]; then zcat "$L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz" > /out/lib/seq.lib; else cp "$L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /out/lib/seq.lib; fi
for f in AO_RVT_TT_nldm_211120 INVBUF_RVT_TT_nldm_220122 OA_RVT_TT_nldm_211120 SIMPLE_RVT_TT_nldm_211120; do zcat "$L/asap7sc7p5t_$f.lib.gz"; done > /out/lib/comb.lib
python3 - <<"PY"
from pathlib import Path
b=Path("/out/lib");txt=(b/"comb.lib").read_text()+(b/"seq.lib").read_text()
import re
libs=re.split(r"(?m)^library\s*\(",txt);head="library ("+libs[1].split("cell (",1)[0];cells=[]
for l in libs[1:]:
 body="cell ("+l.split("cell (",1)[1];body=body[:body.rstrip().rfind("}")];cells.append(body)
(b/"all.lib").write_text(head+"\n".join(cells)+"\n}\n")
PY
yosys -Q -T -l /out/synth.log -s /out/synth.ys > /out/yosys.stdout 2>&1; echo rc=$? > /out/rc
chown -R "$HUID:$HGID" /out
'
