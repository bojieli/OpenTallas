#!/bin/bash
cd /
set -eu
D=/srv/opentallas-scratch2/claude/kv-types-6/pc_detail
W=$D/pdn_all; mkdir -p $W
C=/srv/opentallas-scratch2/claude/codex-kv-types-1113/pc_pg
for m in qkd_kvs_pcc qkd_kvs_pcf qkd_kvs_pcc_h_head_p qkd_kvs_pcf_h_head_p; do
  sed -E "s/^MACRO $m\b/MACRO ${m}_K6/; s/^(\s*)FOREIGN $m\b/\1FOREIGN ${m}_K6/; s/^END $m\b/END ${m}_K6/" $D/$m/detail_view.lef > $W/${m}_K6.lef
  grep -n "^MACRO\|^END ${m}_K6" $W/${m}_K6.lef | head -3
done
cat > $W/pdn.tcl <<'TCL'
read_db /parent/2_3_floorplan_tapcell.odb
foreach m {qkd_kvs_pcc qkd_kvs_pcf qkd_kvs_pcc_h_head_p qkd_kvs_pcf_h_head_p} { read_lef /w/${m}_K6.lef }
set db [ord::get_db]; set block [ord::get_db_block]
foreach i {u_bound.u_kvpc0 u_bound.u_kvpc0_f u_bound.u_kvpc1 u_bound.u_kvpc1_f u_bound.u_kvpc2 u_bound.u_kvpc2_f u_bound.u_kvpc3 u_bound.u_kvpc3_f} {
  set inst [$block findInst $i]; set o [[$inst getMaster] getName]
  set r [$db findMaster ${o}_K6]
  if {$r eq "NULL"} {error "no master ${o}_K6"}
  if {![$inst swapMaster $r]} {error "swap failed $i"}
  puts "SWAP $i $o"
}
source /parent/pdn.tcl
pdngen
puts "PDNGEN_DONE"
exit
TCL
set +e
docker run --rm --name kv6-pdn-all --memory 80g -v "$W:/w" -v "$C/parent:/parent:ro" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /w/pdn.tcl > $W/pdn.log 2>&1
echo "rc=$?" >> $W/pdn.log
