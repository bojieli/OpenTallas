#!/bin/bash
set -euo pipefail
G=/srv/opentallas-scratch/claude/ref_gate/dsdv_gunit_l5-20261019-121901
A=/srv/opentallas-scratch/claude/s81-gunit-mapped-audit-1019
sha256sum "$G/routes/gate/work/orfs/results/asap7/opentallas_dsdv_gunit_l5_asap7_ref_gate/base/1_synth.odb" "$G/routes/gate/work/orfs/results/asap7/opentallas_dsdv_gunit_l5_asap7_ref_gate/base/1_2_yosys.v" > "$A/source_hashes.txt"
docker run --rm -v "$G:/gate:ro" -v "$A:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/dump.tcl > "$A/dump.log" 2>&1
python3 "$A/census.py" "$A/native_pins.tsv" "$A/census.json" > "$A/census.log"
sha256sum "$A"/dump.tcl "$A"/census.py "$A"/native_pins.tsv "$A"/census.json > "$A/proof_hashes.txt"
