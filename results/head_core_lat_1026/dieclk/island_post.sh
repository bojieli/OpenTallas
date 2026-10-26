#!/bin/bash
# die_clock_mesh post-GRT chain: per corner mesh transient -> stub STA (routed RC, terminal caps restored) -> report.
# usage: die_clock_mesh_post.sh <build dir after combo> <plan>   (CORNERS="TT FF" default)
# CLOCK-MESH post-GRT chain per corner: stub-net SPEF (native NDR R + profile C, terminal caps restored, Codex method),
# mesh linear-RC transient driven by the routed tree arrivals, OpenSTA stub->tap, then the related-pair report.
set -e
O=$(readlink -f $1); PLAN=$2; T=/srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/tools/die_plan
NDRW=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['meta']['ndr'].rstrip('w'))" $O/mesh.json)
# needs numpy + scipy on PYTHONPATH
for c in ${CORNERS:-TT FF}; do
  python3 /srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/tools/s81_head/island_clock_mesh.py --spec /srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/results/head_core_lat_1026/island_spec.json mesh $O --corner $c
  python3 /srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/tools/s81_head/island_clock_mesh.py --spec /srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/results/head_core_lat_1026/island_spec.json stubsta $O --corner $c
  python3 - $O/native_$c.spef $O/stubnative_$c.spef <<PY
import sys; sys.path.insert(0, "$T")
from mix_clock_spef import header, sections
src, dst = sys.argv[1:3]
with open(src) as f, open(dst, "w") as g:
    keep = set(open("$O/stub_nets.txt").read().split()); h, names, first = header(f); assert not names; g.writelines(h); n = 0
    for name, lines in sections(f, first, names):
        if name in keep: g.writelines(lines); n += 1
print("stub nets", n)
PY
  python3 $T/restore_clock_spef_caps.py $O/stubnative_$c.spef --out $O/stubs_$c.spef --width $NDRW
  docker run --rm --name ckmesh-sta-$(basename $O)-$c-$$ --cpus=4 --memory=16g --memory-swap=16g -v $O:/out openroad/orfs:latest \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; sta -no_init -exit /out/stubs_$c.tcl > /out/stubs_$c.log 2>&1; chown -R $(id -u):$(id -g) /out"
  tail -3 $O/stubs_$c.log
done
python3 /srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/tools/s81_head/island_clock_mesh.py --spec /srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/results/head_core_lat_1026/island_spec.json report $O --plan $PLAN
