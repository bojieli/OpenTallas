#!/bin/bash
# Execute the selected six-position calendar's real stage-link mechanism.
# Run on the fleet from a source-bound calendar-tool root. XSTAGE is an existing
# source-pinned tools/xdie_s81_2/stage.sh output, never a progressing build dir.
set -euo pipefail
: "${XSTAGE:?set XSTAGE to the pinned xdie source stage}"
: "${CAL_DIR:?set CAL_DIR to the corrected calendar directory}"
: "${LINKS:?set LINKS to the captured source-map link identity}"
OUT=${OUT:-position_link_replay}
PLAN=$OUT/plans
mkdir -p "$PLAN"
python3 tools/s81_dv/tokfunc/mu_hop_plan.py --cal-dir "$CAL_DIR" --links "$LINKS" \
  --hops 1 --modes mtp --preserve-idle --out "$PLAN" > "$OUT/compile.log"
P=$(realpath "$PLAN/mtp_h001_R001A_R002A.json")
O=$(realpath "$OUT")
# Calibration is explicit: exact data/tag/order/fault checks execute, LAND records
# measure every actual transport age, but zero deadlines do not qualify timing.
(cd "$XSTAGE" && python3 tools/xdie_s81_2/gen_golden.py --xl5 --reserve-mu-tag \
  --per S=1.345,N=1.345,H=1.345 --gap 100 --mu-hop-plan "$P" --out "$O/golden") > "$OUT/generate.log"
python3 - "$P" "$O/golden" "$O/capacity.json" <<'PY'
import collections,json,math,sys
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text()); d=Path(sys.argv[2]); g=json.loads((d/'golden.json').read_text())
assert p['compiled_position_graph'] and p['gap_compress']['gaps_compressed']==0
assert sorted({x['position'] for x in p['msgs']})==list(range(6))
counts=collections.Counter()
for line in (d/'stim.hex').read_text().splitlines():
    # The final 276 hex digits are the 1104-bit packet; preceding byte is dp.
    counts[int(line[-278:-276],16)]+=1
# HOP's complete-message arrival is in the emitted graph. Use the exact final
# message issue plus this graph's complete-message receive age and existing drain.
transport=math.ceil(p['modeled_message_receive_age'])
maxcyc=math.ceil(g['last_issue']+transport+2000)
r=dict(NSMAX=int((d/'NS').read_text())+1,NMMAX=int((d/'NM').read_text())+1,
       QD=max(counts.values())+1,MAXCYC=maxcyc,transport_guard=transport,drain=2000,
       derived_from='actual emitted stimuli, per-endpoint inventory and last issue',
       scope='six positions of isolated real stage-link RTL; not stage compute or full token',
       timing_grade='calibration: actual LAND cycles; no deadline qualification')
Path(sys.argv[3]).write_text(json.dumps(r,indent=2)+'\n')
PY
read -r NS NM QD MC < <(python3 - "$OUT/capacity.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); print(r['NSMAX'],r['NMMAX'],r['QD'],r['MAXCYC'])
PY
)
# Unique source stage and output keep all earlier builds intact. Reuse only the
# exact binary/config from this output when it already exists.
B=position6
if [ ! -x "$O/$B/obj/Vtb_xdie_s81_2" ]; then
  (cd "$XSTAGE" && J=${JOBS:-8} bash tools/xdie_s81_2/xdie2.sh build "$O" "$B" g7 \
    -GMU=2 -GXL5=1 -GD_CH=243 -GD_ST=258 -GLRXS=1 -GLINP=1 -GLN32=1 \
    -GNSMAX="$NS" -GNMMAX="$NM" -GQD="$QD" -GMAXCYC="$MC") > "$OUT/build.log" 2>&1
fi
(cd "$XSTAGE" && bash tools/xdie_s81_2/xdie2.sh run "$O" "$B" six_positions "$O/golden") > "$OUT/replay.log" 2>&1
