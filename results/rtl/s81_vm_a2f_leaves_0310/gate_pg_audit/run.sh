set -eu
for n in s81_a2f_fault_join4_native_0310_r1 dsfd_vm_a2f_rsched_p_native_0310_r1 s81_a2_w0_header_native_0310_r2; do
 p=$(find /srv/opentallas-scratch/claude/ref_gate -maxdepth 1 -name "$n-*" | sort | head -1)
 odb=$(find "$p/routes" -name 4_cts.odb | head -1)
 test -s "$odb"
 sha256sum "$odb"
 if ! test -s "$n.log"; then
 docker run --rm -v "$p:/input:ro" -v "$PWD:/audit" -e "AUDIT_ODB=/input/${odb#"$p/"}" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /audit/pg.tcl > "$n.log" 2>&1
 fi
 echo "$n"
 grep ACTUAL_PG "$n.log"
done
