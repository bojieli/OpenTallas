#!/bin/bash
# DIE-QC-36 E2: legal re-sited tree + router-track backbone (bb1), no PG access, all stages.
# If bb1 has unresolved pins, they are run WITHOUT a record (default column window) in a DIAGNOSTIC copy (status relabelled,
# failures kept in the file) -> measures the remaining stage, not a qualification.
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc36; S=$Q/die-qc34; C=$Q/codex-qc-import-0824; M=$Q/codex-qc-mesh5-1029; PC=$Q/codex-qc-provider-clock-0834
O=$R/prebuild_e2_backbone_noaccess; mkdir -p $O
python3 -c "
import json; p=json.load(open(\"$R/backbone_bb1/backbone_plan.json\")); p[\"source_status\"]=p[\"status\"]; p[\"status\"]=\"PASS_GEOMETRY\"; p[\"diagnostic_partial\"]=bool(p[\"failures\"]); json.dump(p,open(\"$O/backbone_plan_e2.json\",\"w\"))"
docker run --rm --name dqc36-e2-$$ --memory=64g --memory-swap=64g --cpus=4 -v "$Q:$Q" -w "$R" python:3.12 bash -c "set -e; trap \"chown -R 1000:1000 $O\" EXIT; pip -q install matplotlib shapely numpy pyyaml jsonschema >/dev/null 2>&1; cd $S/src_pc/tools/clk; python fixed_tree_provider.py --base-adapter $M/src/results/qc_clock_physical_1029/fixed_tree.py --repo $S/src_pc --provider-clock-loads $PC/access2_jointpg/clock_loads_access.json --provider-bindings $Q/qc-import-1/bound/bindings.json --provider-via-facts $M/census119_h800/probe_census.json --native-clock-landings $Q/die-qc29/formA/census_full/landing_plan.json --phy-clock-stubs $Q/die-qc30/b1/phy_stub_plan.json --tree $R/resite/tree_resite.json --netlist $C/reachfix/mechanics/clkonly.v --lef $Q/codex-qc-physical-1029/inputs/cells.lef --plan $Q/qc-import-1/plan/plan_qc_import1.json --endpoints $C/reachfix/mechanics/endpoints.json --tech-vias $M/census119_h800/probe_census.json --backbone-plan $O/backbone_plan_e2.json --out $O > $O/run.log 2>&1"
