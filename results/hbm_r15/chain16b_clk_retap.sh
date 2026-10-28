set -euo pipefail
cd /srv/opentallas-scratch2/claude/hbm-r15-1027
Q=/srv/opentallas-scratch2/claude/hbm-mu-quad-7-1027
python3 tools/incore_restation.py c16 > c16/incore_restation.log
python3 $Q/relax_route.py c16 400 405 --noadd > c16/relax_route2.log
python3 $Q/relax_hop.py c16 400 405 > c16/relax_hop2.log
sha256sum c16/die_plan.json > c16/die_plan.sha256
mkdir -p c16/gates2
C=/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan/check.py
cd c16
python3 $C die_plan.json --out gates2/br_g0 > gates2/br_g0.log 2>&1; echo $? > gates2/br_g0.exit &
python3 $C die_plan.json --completeness --out gates2/br_g0c > gates2/br_g0c.log 2>&1; echo $? > gates2/br_g0c.exit &
wait
set -eu
cd /srv/opentallas-scratch2/claude/hbm-r15-1027
rm -rf c16clk
python3 tools/apply_clk.py c16 c16clk c16clk_report.json --macros c16/core_macros.json --halo 0 > c16clk.log 2>&1
sha256sum c16clk/die_plan.json > c16clk/die_plan.sha256
mkdir -p c16clk/gates
C=/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan/check.py
cd c16clk
python3 $C die_plan.json --out gates/br_g0 > gates/br_g0.log 2>&1; echo $? > gates/br_g0.exit &
python3 $C die_plan.json --completeness --out gates/br_g0c > gates/br_g0c.log 2>&1; echo $? > gates/br_g0c.exit &
wait
set -eu
cd /srv/opentallas-scratch2/claude/hbm-r15-1027
until test -s c16clk/die_plan.sha256; do sleep 5; done
rm -rf c16r; rsync -a --exclude gates c16clk/ c16r/
python3 tools/retap.py c16r > c16r/retap.log
sha256sum c16r/die_plan.json > c16r/die_plan.sha256
mkdir -p c16r/gates; cd c16r
C=/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan/check.py
( python3 $C die_plan.json --out gates/br_g0 > gates/br_g0.log 2>&1; echo $? > gates/br_g0.exit ) &
( python3 $C die_plan.json --completeness --out gates/br_g0c > gates/br_g0c.log 2>&1; echo $? > gates/br_g0c.exit ) &
wait
