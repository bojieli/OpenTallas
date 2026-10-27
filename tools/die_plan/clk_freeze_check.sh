#!/bin/bash
# FLOW-CLKFREEZE 2026-10-27: BLOCKING clock-net geometry check of a post-route ECO dir (all dies' ECO chains).
#   clk_freeze_check.sh D [IMAGE]
# Needs D/clk_freeze.tcl D/clk_dump_db.tcl D/clk_geom_diff.py (staged by the chain) and RESULTS/clk_freeze_pre.tsv +
# clk_freeze_nets.txt written by ot_clk_freeze inside the ECO session (= the routed DB the ECO started from).
# Dumps the ECO's final DB (6_final.odb, else 5_route.odb, else 5_2_route.odb) and diffs: any clock-net wire / pin /
# instance change -> FAIL, net list on stdout, D/clk_geom_diff.json.  Exit 0 PASS, 1 FAIL, 2 cannot check (= FAIL).
set -uo pipefail
D=$(cd "$1" && pwd); IMAGE=${2:-${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
B=$(ls -d "$D"/run/results/asap7/*/base 2>/dev/null | head -1)
test -n "$B" || { echo "CLK_GEOM_DIFF FAIL: no results dir in $D"; exit 2; }
for f in clk_freeze.tcl clk_dump_db.tcl clk_geom_diff.py; do test -f "$D/$f" || { echo "CLK_GEOM_DIFF FAIL: $D/$f not staged"; exit 2; }; done
test -s "$B/clk_freeze_pre.tsv" || { echo "CLK_GEOM_DIFF FAIL: $B/clk_freeze_pre.tsv missing (ot_clk_freeze never ran in the ECO)"; exit 2; }
DB=; for f in 6_final.odb 5_route.odb 5_2_route.odb; do test -s "$B/$f" && { DB=$f; break; }; done
test -n "$DB" || { echo "CLK_GEOM_DIFF FAIL: no routed DB in $B"; exit 2; }
R=${B#$D/}
$DK run --rm --memory=16g --cpus=2 -v "$D":/work -e OT_DB=/work/$R/$DB -e OT_OUT=/work/$R/clk_freeze_post.tsv \
  -e OT_TAG="post:$DB" -e OT_NETS=/work/$R/clk_freeze_nets.txt "$IMAGE" bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/clk_dump_db.tcl" > "$D/clk_freeze_post.log" 2>&1
$DK run --rm -v "$D":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work/$R >/dev/null 2>&1
test -s "$B/clk_freeze_post.tsv" || { echo "CLK_GEOM_DIFF FAIL: post dump failed ($D/clk_freeze_post.log)"; tail -n 5 "$D/clk_freeze_post.log"; exit 2; }
python3 -I "$D/clk_geom_diff.py" "$B/clk_freeze_pre.tsv" "$B/clk_freeze_post.tsv" --json "$D/clk_geom_diff.json"
