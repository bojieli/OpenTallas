#!/usr/bin/env bash
# DIE-HBM-96: real parent floorplan, swap one master for the M6-detail abstract, run the parent's own pdn.tcl. Args: TAG KIT MASTER LEF
set -u
T=$1; K=$2; M=$3; L=$4
P=/srv/opentallas-scratch2/claude/die-hbm-96/pdnp/$T; mkdir -p $P; cd $P
sed -E "s/\b$M\b/${M}_H96/g" $L > ${M}_H96.lef
O=$(ls $K/run/results/asap7/*/base/2_3_floorplan_tapcell.odb 2>/dev/null | head -1); [ -z "$O" ] && O=$(ls $K/run/results/asap7/*/base/2_floorplan.odb | head -1); echo ODB $O; ls -la $O | cut -c25-
B=$(dirname $O)
cat > pdn.tcl <<TCL
read_db /odb/$(basename $O)
read_lef /w/${M}_H96.lef
set db [ord::get_db]; set block [ord::get_db_block]; set n 0
foreach inst [\$block getInsts] { if {[[\$inst getMaster] getName] eq "$M"} {
  set r [\$db findMaster ${M}_H96]; if {![\$inst swapMaster \$r]} {error "swap failed [\$inst getName]"}; incr n; puts "SWAP [\$inst getName]" } }
puts "SWAPPED \$n"
foreach net [\$block getNets] { if {[\$net getSigType] in {POWER GROUND}} { odb::dbSWire_destroy_all_if_any \$net } }
source /work/pdn.tcl
pdngen
puts PDNGEN_DONE
exit
TCL
sed -i '/dbSWire_destroy_all_if_any/d' pdn.tcl
timeout 500 docker run --rm --name h96_pdn_$T --memory=48g --cpus=8 -v $P:/w -v $K:/work -v $B:/odb openroad/orfs:asap7lock bash -c "cd /work; export OBJECTS_DIR=/tmp RESULTS_DIR=/odb LOG_DIR=/tmp; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 8 -exit /w/pdn.tcl" > pdn.log 2>&1; echo RC $?
grep -cE '^\[ERROR' pdn.log; grep -E 'SWAPPED|PDNGEN_DONE|^\[ERROR|^Error' pdn.log | cut -c1-200 | head -12; grep -c 'PDN-0007' pdn.log; grep -E 'PDN-0179|PDN-0006|PDN-0178' pdn.log | head -4 | cut -c1-160
