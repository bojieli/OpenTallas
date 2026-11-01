#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-hbm-clock
for v in NW_A NW_B NE_A NE_B; do
 p=${v:0:2};O=$R/matched_mesh/$v;mkdir -p "$O"
 if [[ "$p" = NW ]]; then M=/srv/opentallas-scratch2/claude/hbm-hubmesh-7/drtv2_a3e6s_NW; else M=$R/NE_source; fi
 cp "$R/$p/pilot.json" "$O/pilot.json"
 for c in TT FF; do
  read -r rise fall < <(python3 -c 'import json,sys;j=json.load(open(sys.argv[1]))[sys.argv[2]]["corners"][sys.argv[3]];print(j["root_rise_slew_ps"],j["root_fall_slew_ps"])' "$R/physical_feed_receipts.json" "$v" "$c")
  docker run --rm --name codex-matched-$v-$c --memory=4g --memory-swap=4g --cpus=2 -e CORNER="$c" -e ROOT_RISE="$rise" -e ROOT_FALL="$fall" -v "$M:/mesh:ro" -v "$O:/out" -v "$R/mesh_matched.tcl:/script.tcl:ro" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 2 -exit /script.tcl > /out/matched_$CORNER.log 2>&1'
 done
 docker run --rm --name codex-matched-mc-$v --memory=8g --memory-swap=8g --cpus=4 -v "$R:$R" -v /srv/opentallas-scratch2/claude/hbm-hubmesh-1/pylib:/pylib:ro -e PYTHONPATH=/pylib openroad/orfs:asap7lock bash -lc "set -e; python3 $R/tools/clk/ot_clk.py rec $R/hbm_hubmesh_a3e6s.yaml --trial $O --stage drt > $O/rec.log 2>&1; python3 $R/fall_rec.py $O; for c in TT FF; do python3 $R/tools/die_plan/explicit_mesh_signoff.py mc $O/rec_drt.json --thev $R/thev_m1.json --corner \$c --samples 60 --jobs 2 --out $O/mc_\$c.json > $O/mc_\$c.log 2>&1; python3 $R/tools/die_plan/explicit_mesh_signoff.py mc $O/rec_drt_fall.json --thev $R/thev_m1.json --corner \$c --samples 0 --jobs 1 --out $O/fall_\$c.json > $O/fall_\$c.log 2>&1; done"
 echo "MATCHED_CASE_DONE $v"
done
