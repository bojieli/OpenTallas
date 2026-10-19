#!/bin/bash
# Read-only actual ODB audit, through ot-run. gate-root and audit source dir.
set -euo pipefail
R=$(realpath "$1");P=$(realpath "$2")
C=$R/routes/gate/work/orfs
B=$C/results/asap7/opentallas_dsdv_sh_lk_asap7_ref_gate/base
ODB=
for f in 4_cts.odb 3_place.odb 3_3_place_gp.odb 3_2_place_iop.odb 2_floorplan.odb;do
 if [ -f "$B/$f" ];then ODB=$f;break;fi
done
[ -n "$ODB" ] || { echo 'No actual placed ODB';exit 2; }
cp "$P/inventory.tcl" "$C/escape_inventory.tcl"
/usr/bin/docker run --rm -v "$C":/work \
 -e ESCAPE_ODB="/work/results/asap7/opentallas_dsdv_sh_lk_asap7_ref_gate/base/$ODB" \
 -e ESCAPE_OUT=/work/escape_inventory.tsv \
 openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 \
 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/escape_inventory.tcl > "$R/escape_inventory.log" 2>&1
python3 "$P/escape_capacity.py" "$C/escape_inventory.tsv" "$R/escape_capacity.json"
