#!/bin/bash
set -u
SRC=/srv/opentallas-scratch2/claude/codex-hbm-quarter-keep-1445/source
OUT=/srv/opentallas-scratch2/claude/codex-hbm-quarter-keep-1445
NAME=quarter_residual
MEMG=48
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
docker run --rm -e OT_KEEP_PIN_REGS=1 -e DESIGN_NAME=ot_hnx_idxn_quarter_with_keybuf --name hdie15-$NAME-$$ --cpus=4 --memory=${MEMG:-96}g -v $SRC:/src:ro -v $OUT:/out -w /src openroad/orfs:asap7lock bash -lc "
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; mkdir -p /tmp/lib;
  zcat $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz > /tmp/lib/seq.lib 2>/dev/null || cp $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib /tmp/lib/seq.lib;
  for f in AO_RVT_TT_nldm_211120 INVBUF_RVT_TT_nldm_220122 OA_RVT_TT_nldm_211120 SIMPLE_RVT_TT_nldm_211120; do zcat $L/asap7sc7p5t_\$f.lib.gz; done > /tmp/lib/comb.lib;
  python3 - <<'PY2'
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
PY2
  yosys -q -l /out/$NAME.log -s /out/$NAME.ys" > $OUT/$NAME.docker.log 2>&1
rc=$?
echo "$NAME rc=$rc $(grep -m1 'Chip area' $OUT/$NAME.stat 2>/dev/null)"
exit $rc
