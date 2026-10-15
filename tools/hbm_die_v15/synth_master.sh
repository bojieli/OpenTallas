#!/bin/bash
# H-DIE v15 (2026-10-15): synthesise ONE die master to a gate netlist for (a) outline/pin grants (cell area, FF count,
# macro count) and (b) composed die-subnet elaboration over netlists instead of source (source elaboration of the SW
# subnet timed out twice: 5,000 s / 3,300 s).
#   synth_master.sh <src root> <out dir> <name> <top> <params k=v,...|-> <blackbox mods comma|-> [--prefer FILE]
# File list: tools/hbm_die_v15/master_filelist.py (mapped memory macros read -lib from their _bb.v).
# Yosys in the ORFS asap7lock image, RVT TT liberty; synth -flatten, dfflibmap, abc; writes
#   <name>.stat (stat -liberty), <name>.netlist.v (write_verilog -noattr, top keeps its RTL port list), <name>.files.json
set -u
mkdir -p $2; SRC=$(readlink -f $1); OUT=$(readlink -f $2); NAME=$3; TOP=$4; PRM=$5; BB=$6; shift 6
PREF=""; [ "${1:-}" = "--prefer" ] && PREF="--prefer $SRC/$2"
BBARG=""; [ "$BB" != "-" ] && BBARG="--bb $BB"
mkdir -p $OUT
HDIE_ALLOW_AMBIGUOUS=1 python3 $SRC/tools/hbm_die_v15/master_filelist.py $TOP --root $SRC --json $PREF $BBARG > $OUT/$NAME.files.json || { echo "$NAME FILELIST_FAIL"; exit 2; }
python3 - "$OUT/$NAME.files.json" "$OUT/$NAME.ys" "$TOP" "$PRM" "$BB" "$NAME" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); ys=sys.argv[2]; top=sys.argv[3]; prm=sys.argv[4]; bb=sys.argv[5]; name=sys.argv[6]
L=[]
for m in d['macros']: L.append(f"read_verilog -lib {m['file']}")
for f in d['files']: L.append(f"read_verilog -sv -DSYNTHESIS {f}")
for b in ([] if bb=='-' else bb.split(',')):
    if b: L.append(f"blackbox {b}")
if prm!='-':
    for kv in prm.split(','):
        k,v=kv.split('='); L.append(f"chparam -set {k} {v} {top}")
L += [f"hierarchy -check -top {top}", f"tee -o /out/{name}.hier.stat stat",
      f"synth -top {top} -flatten", "dfflibmap -liberty /tmp/lib/seq.lib", "abc -liberty /tmp/lib/all.lib", "opt_clean",
      f"tee -o /out/{name}.stat stat -liberty /tmp/lib/all.lib", f"write_verilog -noattr /out/{name}.netlist.v"]
open(ys,'w').write("\n".join(L)+"\n")
PY
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
docker run --rm --name hdie15-$NAME-$$ --cpus=4 --memory=${MEMG:-96}g -v $SRC:/src:ro -v $OUT:/out -w /src openroad/orfs:asap7lock bash -lc "
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
