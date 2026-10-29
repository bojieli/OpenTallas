#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-qc-1029/baseline26
K=$D/trial26
A=$D/c26
R=$D/g26
TI=$D/current_source/tools
MT=$TI/die_plan
CA=/srv/opentallas-scratch2/claude/die-qc9-1028/ca
MAP=$D/part_region.json
PLAN=$D/plan/ev_qc25.json
mkdir -p "$R/run"
ln -s "$K/clock" "$R/run/clk"
for C in TT FF; do ln -s "${A}_$C" "$R/run/out_$C"; done
python3 -I "$TI/s81_head/landed_phase_ocv.py" "$PLAN" "$R/run" --tools "$MT" --clock-cell inv2 --out "$R/lpo.json" > "$R/lpo.log" 2>&1
cd "$R"
PYTHONPATH=$MT python3 "$CA/ca_spice.py" "$R/lpo.json" "$MAP" "$R/grp_spice" 0.9324 0.9380 --mc 0 > "$R/ca.log" 2>&1
python3 -I "$CA/mk_proof.py" "$R/run" "$MAP" "$R/proof0" > "$R/proof.log" 2>&1
for C in TT FF; do
 python3 - "$R/proof0/tap_arrivals_$C.json" <<'PY'
import json,sys
p=sys.argv[1];d=json.load(open(p));d['clock_cell']='inv2';json.dump(d,open(p,'w'))
PY
done
mkdir -p "$R/proof"
cp "$R/proof0/droop_regions.json" "$R/proof0/mesh.json" "$R/proof/"
for C in TT FF; do
 python3 -I "$MT/tap_fall_merge.py" "$R/proof0" "$C" "${A}_$C/arr_$C.txt" --out "$R/pf_$C" --tree "$K/clock/tree.json" > "$R/fall_$C.log" 2>&1
 cp "$R/pf_$C/tap_arrivals_$C.json" "$R/proof/"
done
echo QC26_PROOF_READY
