#!/bin/bash
# KV-AHUB2 10-19: mapped (ASAP7 RVT TT) synthesis of the grouped AHUB transport, copy of tools/qwen_kv_die/ahub_safe/synth.sh
#   synth_map.sh <src dir> <out dir> <name> <top> <bb|-> <params k=v,..|-> <files...>  (fleet only, docker orfs:asap7lock)
set -eu
set -o pipefail
SRC=$(readlink -f $1); OUT=$(readlink -f $2); NAME=$3; TOP=$4; BB=$5; PRM=$6; shift 6
mkdir -p $OUT
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
# Same register-keep treatment as every ref_tile kit synthesis: ORFS SYNTH_CANONICALIZE_TCL =
# physical/common_flow/ot_keep_regs.tcl (keep on every flop that drives a (* keep *) wire, so opt_merge cannot fold the
# declared copies).  KEEP_REGS=0 reproduces the plain flow (attempt map1: copies folded, 553-load reset term).
KR=${KEEP_REGS:-1}
cp $(dirname $(readlink -f $0))/ot_keep_regs.tcl $OUT/ot_keep_regs.tcl
{
  echo "yosys read_verilog -sv -DSYNTHESIS $*"
  [ "$BB" != "-" ] && for b in ${BB//,/ }; do echo "yosys blackbox $b"; done
  [ "$PRM" != "-" ] && for kv in ${PRM//,/ }; do echo "yosys chparam -set ${kv%%=*} ${kv#*=} $TOP"; done
  echo "yosys hierarchy -check -top $TOP"
  [ "$KR" = 1 ] && echo "source /out/ot_keep_regs.tcl"
  echo "yosys synth -top $TOP -flatten ${NOSHARE:+-noshare}"
  echo "yosys check -assert"
  echo "yosys write_json /out/$NAME.generic.json"
  echo "yosys dfflibmap -liberty /tmp/lib/seq.lib"
  echo "yosys abc -liberty /tmp/lib/all.lib"
  echo "yosys opt_clean"
  echo "yosys read_liberty -lib /tmp/lib/all.lib"
  echo "yosys write_json /out/$NAME.mapped.json"
  echo "yosys write_verilog -noattr /out/$NAME.mapped.v"
  echo "yosys tee -o /out/$NAME.stat stat -liberty /tmp/lib/all.lib"
} > $OUT/$NAME.tcl
docker run --rm --cpus=2 --memory=16g -v $SRC:/src -v $OUT:/out -w /src openroad/orfs:asap7lock bash -lc "
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
  cp /tmp/lib/all.lib /out/cells.lib;
  yosys -q -p 'read_liberty -ignore_miss_func /tmp/lib/all.lib; write_verilog -noattr /out/cells_sim.v';
  yosys -q -l /out/$NAME.log -c /out/$NAME.tcl" > $OUT/$NAME.docker.log 2>&1
echo "$NAME rc=$? $(grep -m1 'Chip area' $OUT/$NAME.stat 2>/dev/null)"
