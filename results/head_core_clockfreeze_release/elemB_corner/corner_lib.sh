#!/bin/bash
# DIE-HEAD-5 KITS34: single-corner timing models of a SIGNED core from its own 6_final.odb/.sdc/.spef (unchanged),
# std-cell lib list = exactly the five RVT libs (same versions) its generate_abstract.log read.
# same commands as its generate_abstract (load + read_sdc 6_final.sdc + read_spef + write_timing_model) but with ONLY
# that corner's std-cell + macro libs loaded, so the lib header/op-cond is the corner's own.  RUN=core run dir, OUT=dir.
set -eu
RUN=$1; MOD=$2; OUT=$3; mkdir -p $OUT
B=$(ls -d $RUN/run/results/asap7/*/base); echo base $B
sha256sum $B/6_final.odb $B/6_final.spef $B/6_final.sdc $B/${MOD}_tc.lib $B/${MOD}_BC.lib > $OUT/inputs.sha256
for C in TT FF; do c=$(echo $C | tr A-Z a-z)
cat > $OUT/cl_$C.tcl <<T
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach s {AO_RVT_${C}_nldm_211120.lib.gz INVBUF_RVT_${C}_nldm_220122.lib.gz OA_RVT_${C}_nldm_211120.lib.gz SEQ_RVT_${C}_nldm_220123.lib SIMPLE_RVT_${C}_nldm_211120.lib.gz} { puts "read_liberty \$L/asap7sc7p5t_\$s"; read_liberty \$L/asap7sc7p5t_\$s }
foreach f [lsort [glob -nocomplain /work/macros/*_${c}.lib]] { puts "read_liberty \$f"; read_liberty \$f }
read_db $B/6_final.odb
read_sdc $B/6_final.sdc
read_spef $B/6_final.spef
write_timing_model /out/${MOD}_${c}.lib
puts OT_CORNER_LIB_DONE
T
sed -i "s#$RUN#/work#g" $OUT/cl_$C.tcl
docker run --rm --memory=16g --memory-swap=16g --cpus=4 -v $RUN:/work:ro -v $OUT:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /out/cl_$C.tcl > /out/cl_$C.log 2>&1; chown -R $(id -u):$(id -g) /out"
tail -1 $OUT/cl_$C.log
done
