#!/usr/bin/env bash
# STEWARD-HBMd/GLUE 2026-10-23: VM-glue split parent hfd_hgi_vms_glue_<k>_s (gen_vms_glue_split.py) == the g7 tile
# (--ref tile) and == the contract ref (--ref ref) in lockstep (vms_glue_split_equiv.py).  pos must print
# "VMS_GLUE_SPLIT_EQUIV <Q> PASS checks=N errors=0"; mutants (rmut g3 g4 g5 g7 split sid) must FAIL.
# Exit status 0 only on a counted PASS.   run_vms_glue_split_equiv.sh Q tile|ref pos|<mut> OUT
set -uo pipefail
cd "$(dirname "$0")/../.."
q=${1:?quadrant}; r=${2:?tile|ref}; m=${3:?pos|mut}; OUT=$(realpath -m "${4:?out}"); mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/hbm_accel/generic/vm/static
src=($S/hfd_hgi_vms_glue_split.sv $S/hfd_hgi_vms_glue_tiles.sv $S/hfd_hgi_vms_glue_tiles_ref.sv $S/hfd_hgi_vms_glue_lt.sv
     $S/hfd_hgi_vms_static_glue.sv $S/ot_vms_hub_static.sv $S/ot_vms_rstop_static.sv $S/ot_vms_rcl_static.sv
     $S/ot_vms_status_static.sv rtl/lib/ot_rst_relay.sv)
TAG=VMS_GLUE_SPLIT_EQUIV
X=; [ "$m" != pos ] && X="--mut $m"
D="$OUT/$q$r$m"
"$V" --version
python3 tools/hbm_die_v16/gen_vms_glue_split.py --check || { echo "$TAG $q GENSTALE"; exit 1; }
python3 tools/hbm_die_v16/vms_glue_split_equiv.py --quadrant $q --ref $r --out "$D" $X > "$D.gen.log" 2>&1 || { cat "$D.gen.log"; echo "$TAG $q GENFAIL"; exit 1; }
cat "$D.gen.log"
"$V" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_vms_glue_split -Mdir "$D/obj" \
  "${src[@]}" "$D/tb_vms_glue_split.sv" > "$D.build.log" 2>&1 || { grep -m5 %Error "$D.build.log"; echo "$TAG $q BUILDFAIL"; exit 1; }
"$D/obj/Vtb_vms_glue_split" > "$D.sim.log" 2>&1
rm -rf "$D/obj"
grep -E "$TAG|MISMATCH" "$D.sim.log" | tail -6
grep -Eq "^$TAG $q PASS checks=[1-9][0-9]* errors=0$" "$D.sim.log"
