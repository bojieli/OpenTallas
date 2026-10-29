#!/bin/bash
# QC-PG-2: SU-window upper-deck combos by exact superposition (results/qc_pg_map_1027/combine.py).
#   combos.sh F_SU8 BG    F_SU8 = su8 measured/vectorless power factor, BG = background W/mm2 (A0 + flattened logic)
# su8 block = blocks with centre in the su8 rect (or the spread rect); interior worst = canonical interior (keepoff 450).
set -eu
W=$(cd $(dirname $0)/../.. && pwd); C=$W/results/qc_pg_map_1027/combine.py
M=/srv/opentallas-scratch2/claude/qc-pg-map-1027/kits; N=/srv/opentallas-scratch2/claude/qc-pg-2-1027/kits
O=/srv/opentallas-scratch2/claude/qc-pg-2-1027/comb; mkdir -p $O
f=$1; bg=$2; fm=$(python3 -c "print($f-1)"); R1=1581.1,1330.6,1753.9,1460.2
run() { # tag evalrect S U8 U8new A F   (U8new set: su8 load moved to the spread outline -> S - U8 + f*U8new)
  if [ -n "$5" ]; then cls="S=$3:1 U=$4:-1 V=$5:$f A=$6:$bg F=$7:$bg"; else cls="S=$3:1 U=$4:$fm A=$6:$bg F=$7:$bg"; fi
  python3 $C $O/$1_f${f}_bg${bg}_su8.json 450 $cls --eval $2 | python3 -c "import json,sys;d=json.load(sys.stdin);print('$1 f $f bg $bg','su8blk',d['interior_worst'])"
  python3 $C $O/$1_f${f}_bg${bg}_int.json 450 $cls | python3 -c "import json,sys;d=json.load(sys.stdin);print('$1 f $f bg $bg','interior',d['interior_worst'])"
}
b=M9w672_p70_SU
run base $R1 $M/S/$b/psm $M/U8/$b/psm "" $M/A/$b/psm $M/F/$b/psm
run K75suc $R1 $N/S/K75suc/psm $N/U8/K75suc/psm "" $N/A/K75suc/psm $N/F/K75suc/psm
run K75su8 $R1 $N/S/K75su8/psm $N/U8/K75su8/psm "" $N/A/K75su8/psm $N/F/K75su8/psm
run SP2 1581.1,1330.6,1753.9,1589.8 $M/S/$b/psm $M/U8/$b/psm $N/U8/SP2/psm $M/A/$b/psm $M/F/$b/psm
run SP4 1581.1,1330.6,1753.9,1849.0 $M/S/$b/psm $M/U8/$b/psm $N/U8/SP4/psm $M/A/$b/psm $M/F/$b/psm
