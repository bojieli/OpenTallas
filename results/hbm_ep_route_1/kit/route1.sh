#!/bin/bash
# HBM-EP-ROUTE-1 hfd_ep_static: do-cts (plan tree + 12.8c 4xBUFx16f entry trunk) -> FF hold gate + placement-RC insertion ->
# GRT (FF hold repair, kit recipe) -> post-CTS gates (info) -> DRT -> fill -> finish -> abstract -> signoff.py (RCX, TT/FF) ->
# RCX insertion + S-trunk probe -> post-route LEC of 6_final.v.  Run via ot-run; logs in KIT/route1.log.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); exec >> "$K/route1.log" 2>&1
echo "ROUTE1 start $(date -Is)"
IMG=openroad/orfs:asap7lock
docker run --rm --name eproute1-$$ --cpus=16 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16\"; R=/work/run/results/asap7/hbc_hfd_ep_static/base; PD=/OpenROAD-flow-scripts/flow/platforms/asap7; \
 \$M do-cts; rc=\$?; echo ROUTE1_CTS rc=\$rc; grep -h OT_MSCTS_BUILD.*entry /work/run/logs/asap7/*/base/4_1_cts.log; \
 if [ \$rc = 0 ]; then PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n \"s/^BC_LIB_FILES *[:=] *//p\")\" ODB=\$R/4_cts.odb SDC=\$R/4_cts.sdc PLATFORM_DIR=\$PD OT_VCLK_TT=250 OT_VCLK_FF=202.5 LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1; grep OT_HOLD_GATE /work/hold_gate.log; \
   for c in TT FF; do OT_CORNER=\$c ODB=\$R/4_cts.odb SDC=\$R/4_cts.sdc PLATFORM_DIR=\$PD LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl openroad -exit /work/measure_ins_r5.tcl > /work/ins_\$c.log 2>&1; grep OT_R5_INS /work/ins_\$c.log; done; \
   grep -q \"OT_HOLD_GATE PASS\" /work/hold_gate.log || { echo ROUTE1_STOP hold gate; rc=4; }; fi; \
 if [ \$rc = 0 ]; then OT_VCLK_CORNER=ff \$M do-5_1_grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=0; rc=\$?; echo ROUTE1_GRT rc=\$rc; grep -hiE \"hold buffer|RSZ-00(32|46)|GRT-0096|overflow\" /work/run/logs/asap7/*/base/5_1_grt.log | tail -5; fi; \
 if [ \$rc = 0 ]; then for c in TT FF; do OT_POSTCTS_GRT=1 OT_CORNER=\$c ODB=\$R/5_1_grt.odb openroad -exit /work/postcts_gate.tcl > /work/postcts_gate_\$c.log 2>&1; grep -h OT_POSTCTS_GATE /work/postcts_gate_\$c.log | tail -2; done; fi; \
 if [ \$rc = 0 ]; then \$M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc; rc=\$?; echo ROUTE1_DRT rc=\$rc; grep -h \"violations\|DRC\" /work/run/logs/asap7/*/base/5_2_route.log | tail -3; fi; \
 if [ \$rc = 0 ]; then \$M do-finish; rc=\$?; echo ROUTE1_FINISH rc=\$rc; fi; \
 if [ \$rc = 0 ]; then \$M do-generate_abstract; echo ROUTE1_ABSTRACT rc=\$?; ODB=\$R/6_final.odb OUT=/work/routed_clk.txt openroad -python -exit /work/dump_routed_clk.py > /work/dump_routed_clk.log 2>&1; echo ROUTE1_DUMP rc=\$?; fi; \
 chown -R $(id -u):$(id -g) /work; exit \$rc"
rc=$?; echo "ROUTE1_FLOW rc=$rc $(date -Is)"
[ $rc = 0 ] || exit $rc
python3 "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --docker docker > "$K/signoff_run.log" 2>&1; echo "ROUTE1_SIGNOFF rc=$? $(date -Is)"; grep -h "SIGNED\|SIGNOFF" "$K/signoff_run.log" | tail -3
SP=$(find "$K/signoff" -name *.spef | head -1); echo "ROUTE1_SPEF $SP"
R=$K/run/results/asap7/hbc_hfd_ep_static/base
if [ -n "$SP" ]; then for c in TT FF; do docker run --rm --memory=8g -v "$K":/work -v "$(dirname "$SP")":/spef $IMG bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; OT_CORNER=$c ODB=/work/run/results/asap7/hbc_hfd_ep_static/base/6_final.odb SDC=/work/constraint.sdc SPEF=/spef/$(basename "$SP") PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 openroad -exit /work/probe_rcx.tcl" > "$K/probe_rcx_$c.log" 2>&1; grep -h "OT_RCX" "$K/probe_rcx_$c.log"; done; fi
# post-route LEC of the routed netlist (export: drop only portless physical-only cells)
F=$K.lec_final; rm -rf "$F"; mkdir -p "$F"; rsync -a --exclude run/ --exclude lec/ --exclude signoff/ "$K/" "$F/"; V=$R/6_final.v
echo "ROUTE1_FINAL_V $V $(stat -c %y "$V")"
python3 -I - "$V" "$F/final_functional.v" <<PY
import re, sys, json
from pathlib import Path
src, out = map(Path, sys.argv[1:3]); t = src.read_text()
phys = r"(?:TAPCELL_ASAP7_75t_R|FILLER\w*|FILLERxp5\w*|DECAP\w*)"
clean, n = re.subn(r"(?m)^\s*%s\s+\S+\s*\(\s*\);\s*$" % phys, "", t)
left = re.findall(r"(?m)^\s*(%s)\s+\S+" % phys, clean)
if left: raise SystemExit("Refusing physical-only master with ports: %s" % sorted(set(left))[:5])
out.write_text(clean)
out.with_suffix(".physical_only.json").write_text(json.dumps(dict(source=str(src), portless_physical_removed=n, functional_cells_or_nets_changed=0), indent=1)+"\n")
print("ROUTE1_EXPORT portless physical-only removed", n)
PY
python3 -I "$F/lec.py" "$F" --netlist "$F/final_functional.v" --out "$F/lec" --jobs 8 --mem 16 > "$F/lec.run.log" 2>&1 || echo "lec.py rc=$?"
tail -n 1 "$F/lec.run.log"
echo "ROUTE1_DONE $(date -Is)"
