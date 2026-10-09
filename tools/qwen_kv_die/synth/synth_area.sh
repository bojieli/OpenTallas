#!/bin/bash
# kv-die 2026-10-09 (review-0528 item 4): synthesised cell area of the KV-die blocks whose frames were ASSUMED.
#   synth_area.sh <src tree> <out dir> <name> <top> <blackbox modules (comma, or -)> <params (k=v,..., or -)> <files...>
# Yosys (ORFS asap7lock image), RVT TT liberty, flatten, abc; reports `stat -liberty` (um2) into <out>/<name>.stat.
set -u
SRC=$(readlink -f $1); OUT=$(readlink -f $2); NAME=$3; TOP=$4; BB=$5; PRM=$6; shift 6
mkdir -p $OUT
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
{
  echo "read_verilog -sv -DSYNTHESIS $*"
  [ "$BB" != "-" ] && for b in ${BB//,/ }; do echo "blackbox $b"; done
  [ "$PRM" != "-" ] && for kv in ${PRM//,/ }; do echo "chparam -set ${kv%%=*} ${kv#*=} $TOP"; done
  echo "hierarchy -check -top $TOP"
  echo "synth -top $TOP -flatten"
  echo "dfflibmap -liberty /tmp/lib/seq.lib"
  echo "abc -liberty /tmp/lib/all.lib"
  echo "opt_clean"
  echo "tee -o /out/$NAME.stat stat -liberty /tmp/lib/all.lib"
} > $OUT/$NAME.ys
docker run --rm --cpus=4 --memory=96g -v $SRC:/src -v $OUT:/out -w /src openroad/orfs:asap7lock bash -lc "
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; mkdir -p /tmp/lib;
  zcat $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz > /tmp/lib/seq.lib 2>/dev/null || cp $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib /tmp/lib/seq.lib;
  for f in AO_RVT_TT_nldm_211120 INVBUF_RVT_TT_nldm_220122 OA_RVT_TT_nldm_211120 SIMPLE_RVT_TT_nldm_211120; do zcat $L/asap7sc7p5t_\$f.lib.gz; done > /tmp/lib/comb.lib;
  python3 - <<'PY'
import re
txt = open('/tmp/lib/comb.lib').read() + open('/tmp/lib/seq.lib').read()
libs = re.split(r'(?m)^library\s*\(', txt)
head = 'library (' + libs[1].split('cell (', 1)[0]
cells = []
for l in libs[1:]:
    body = l.split('cell (', 1)[1] if 'cell (' in l else ''
    body = 'cell (' + body
    body = body[:body.rstrip().rfind('}')]
    cells.append(body)
open('/tmp/lib/all.lib', 'w').write(head + '\n'.join(cells) + '\n}\n')
PY
  yosys -q -l /out/$NAME.log -s /out/$NAME.ys" > $OUT/$NAME.docker.log 2>&1
echo "$NAME rc=$? $(grep -m1 'Chip area' $OUT/$NAME.stat 2>/dev/null)"
