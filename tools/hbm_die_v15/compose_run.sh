#!/bin/bash
# H-DIE v15: run OUT/compose.ys (tools/hbm_die_v15/compose_netlists.py) in the ORFS asap7lock image.
#   compose_run.sh <src root> <out dir>      -> <out>/compose.log, compose.stat, exit = yosys status
set -u
SRC=$(readlink -f $1); OUT=$(readlink -f $2)
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
docker run --rm --name hdie15-compose-$$ --cpus=4 --memory=${MEMG:-64}g -v $SRC:/src:ro -v $OUT:/work -w /work openroad/orfs:asap7lock bash -lc "
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; mkdir -p /tmp/lib;
  for f in AO_RVT_TT_nldm_211120 INVBUF_RVT_TT_nldm_220122 OA_RVT_TT_nldm_211120 SIMPLE_RVT_TT_nldm_211120 SEQ_RVT_TT_nldm_220123; do zcat $L/asap7sc7p5t_\$f.lib.gz 2>/dev/null || cat $L/asap7sc7p5t_\$f.lib; done > /tmp/lib/cat.lib;
  python3 - <<'PY'
import re
txt=open('/tmp/lib/cat.lib').read()
libs=re.split(r'(?m)^library\s*\(',txt)
head='library ('+libs[1].split('cell (',1)[0]
cells=[]
for l in libs[1:]:
    body='cell ('+(l.split('cell (',1)[1] if 'cell (' in l else '')
    cells.append(body[:body.rstrip().rfind('}')])
open('/tmp/lib/all.lib','w').write(head+'\n'.join(cells)+'\n}\n')
PY
  yosys -q -l compose.log -s compose.ys" > $OUT/compose.docker.log 2>&1
rc=$?
# a resized cell port = the netlist and the subnet disagree on a port width (stale netlist or contract): FAIL
if [ $rc = 0 ] && grep -q "Resizing cell port" $OUT/compose.log; then rc=3; fi
echo "compose rc=$rc $(grep -c 'Warning' $OUT/compose.log 2>/dev/null) warnings"; exit $rc
