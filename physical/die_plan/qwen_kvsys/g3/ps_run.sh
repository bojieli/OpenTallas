#!/bin/bash
# ps_run.sh VARIANT STAGE(4_cts|6_final) CORNER  -> meas/<v>_<stage>_<C>.tsv  (pair skew with CPPR, kit scope)
V=$1; S=$2; C=$3; cd ~/scratch/kv-g3
R=/k/g3/$V/kv3_hub_Ei/run/results/asap7/dp_kv3_hub_Ei/base
T=meas/ps_${V}_${S}_${C}.tcl
{
echo 'set C $::env(CORNER); set P /OpenROAD-flow-scripts/flow/platforms/asap7'
echo 'foreach f [glob $P/lib/NLDM/*_RVT_${C}_*.lib* $P/lib/NLDM/*_LVT_${C}_*.lib*] { if {[string match *FAKE* $f] || [string match *SRAM* $f]} continue; read_liberty $f }'
echo "read_db $R/$S.odb"
if [ $S = 6_final ]; then echo "read_sdc $R/6_final.sdc"; echo "source \$P/setRC.tcl"; echo "read_spef $R/6_final.spef";
elif [ $S = 5_route ]; then echo "read_sdc $R/5_route.sdc"; echo "source \$P/setRC.tcl"; echo "define_process_corner -ext_model_index 0 X"; echo "extract_parasitics -ext_model_file \$P/rcx_patterns.rules";
else echo "read_sdc $R/$S.sdc"; echo "source \$P/setRC.tcl"; echo "estimate_parasitics -placement"; fi
echo 'set ::env(OT_PS_SCOPE) kit'
echo 'source /k/tools/ps/pair_skew.tcl'
} > $T
docker run --rm -v $PWD:/k -e CORNER=$C -e OT_PS_OUT=/k/meas/${V}_${S}_${C}.tsv openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /k/$T" > meas/${V}_${S}_${C}.log 2>&1
chown $(id -u) meas/* 2>/dev/null; echo done $V $S $C
