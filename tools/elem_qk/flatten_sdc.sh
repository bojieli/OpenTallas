#!/bin/bash
# ELEM-QK 10-24: evaluate a ref_tile sign-off SDC (a Tcl program: env-driven, measures the boundary clock arrival L on
# the routed design) on its OWN routed DB at TT and write the resulting constraint set as a plain SDC (OpenSTA
# write_sdc), so tools/die_plan/signoff.py's sdc_lint can judge the constraints themselves.  The numbers are the ones
# the Tcl form computes on this DB; nothing is relaxed or re-derived.
#   flatten_sdc.sh BASE(results/.../base) SIGNOFF_SDC OUT.sdc [IMAGE]
set -euo pipefail
BASE=$(readlink -f $1); SDC=$(readlink -f $2); OUT=$(readlink -f $3); IMG=${4:-openroad/orfs:latest}
W=$(mktemp -d "$(dirname $OUT)/flat.XXXX"); cp $SDC $W/golden.sdc
cat > $W/s.tcl <<TCL
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*] { read_liberty \$l }
foreach l [glob -nocomplain /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_TT_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_TT_*] { if {![string match *FAKE* \$l]} { read_liberty \$l } }
read_db /base/6_final.odb
if {[file exists /base/6_final.spef]} { read_spef /base/6_final.spef }
read_sdc /w/golden.sdc
set_propagated_clock [all_clocks]
write_sdc -no_timestamp -digits 4 /w/flat.sdc
TCL
sudo docker run --rm -v $BASE:/base:ro -v $W:/w $IMG /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /w/s.tcl > $W/log 2>&1 || { tail -n 20 $W/log; exit 1; }
{ echo "# FLATTENED by tools/elem_qk/flatten_sdc.sh from $SDC on $BASE/6_final.odb (TT, OpenSTA write_sdc)"; cat $W/flat.sdc; } > $OUT
echo "flat: $OUT ($(grep -c . $OUT) lines)"
