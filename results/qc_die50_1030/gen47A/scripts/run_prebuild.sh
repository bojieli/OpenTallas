#!/bin/bash
# DIE-QC-50/gen47A step 2: fixed-tree clock prebuild on gen47 (main tools/clk/fixed_tree_provider.py + DIE-QC-41/42
# adapter fixed_tree_prov_f1d_r3.py, copied unmodified from intel2 die-qc41). Recipe = DIE-QC-41 run_f1d_r3.sh (R7BFR3)
# with gen47 inputs. usage: run_prebuild.sh TAG [extra adapter args...]; env: F1 FUT BB (backbone plan) NOBB NL (native landings) ST (phy stubs)
# launch: ot-run --hosts epyc2 --mem 64 --threads 4 --dir $A --priority die -- bash run_prebuild.sh TAG
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; A=$Q/die-qc-50/gen47A; B=$Q/die-qc-50/gen47b; W=$Q/wt/die-qc-50-gen47A
TAG=$1; shift; O=$A/prov_$TAG; mkdir -p $O
AD=$W/results/qc_die50_1030/gen47A/scripts/fixed_tree_prov_f1d_r3.py
EXTRA=""
[ -n "${BB:-}" ] && EXTRA="$EXTRA --backbone-plan $BB"
[ -n "${NL:-}" ] && EXTRA="$EXTRA --native-clock-landings $NL --phy-clock-stubs $ST"
docker run --rm -e OT_DQC40_F1=${F1:-0} -e OT_DQC40_F1RES=0 -e OT_DQC41_FUTURE=${FUT:-} -e OT_DQC41_ROOTX=1 -e OT_DQC41_ROOTRES=1 \
  -e OT_DQC41_FIRST=${FIRST:-} -e OT_DQC41_NOBB=${NOBB:-} -e OT_DQC38_PROV=A -e OT_DQC38_NAT=1 -e OT_DQC38_NEAR_A=8.64 \
  -e OT_DQC39_LANDRES=all -e OT_DQC39_JOGX=2.0 -e OT_G47A_E1DIAG=0 -e OT_G47A_E1DIAG_OUT=$O/e1diag_errors.json --name dqc50g47A-pb-$TAG-$$ --memory=64g --memory-swap=64g --cpus=4 -v $Q:$Q -w $O python:3.12 bash -c "
set -e; trap 'chown -R 1000:1000 $O' EXIT; date; pip -q install matplotlib shapely numpy pyyaml jsonschema >/dev/null 2>&1; cd $W/tools/clk
python fixed_tree_provider.py --base-adapter $AD --repo ${REPO:-$W} \
 --provider-clock-loads $A/${ACC:-access_rs}/plan/clock_loads_access.json --provider-bindings $B/bound/bindings.json \
 --provider-via-facts $A/${ACC:-access_rs}/via_facts.json $EXTRA \
 --tree ${TREE:-$A/resite/tree47_resite.json} --netlist $A/pb_inputs/clkonly47.v --lef $A/inputs/cells.lef --plan $B/inputs/plan_qc49.json \
 --endpoints $B/build/endpoints.json --tech-vias $A/${ACC:-access_rs}/via_facts.json --out $O $* > $O/run.log 2>&1"
