#!/bin/bash
# usage: route.sh TAG OUTDIR PARAMS...  -- ot_dsrom_head_elem routed at 833 ps, WC(SS) setup, WC+BC(FF) hold, 60/25 ps
TAG=$1; O=$2; shift 2
cd /home/ubuntu/claude-scratch/dsrom-recovery-head/${SRCD:-src}
mkdir -p $O
P=''; for x in "$@"; do P="$P --param $x"; done
OT_ORFS_NUM_CORES=20 $HOME/bin/admit.sh 24 -- python3 tools/run_abi3_physical.py --view asap7 --top ot_dsrom_head_elem   --source rtl/v41rom/ot_dsrom_head_elem.sv --source rtl/v41rom/ot_v41_fadd.sv --source rtl/common/ot_prefix.sv   --source rtl/v41rom/ot_v41_bmul2.sv --source rtl/v41rom/ot_dsrom_bmul3.sv --source physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v   $P --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025   --orfs-corner WC --hold-corners WC,BC --orfs-var ADDER_MAP_FILE= --max-transition-ns --max-fanout 32   --stages pnr --false-path-io --core-utilization ${UTIL:-40} --macro-place-halo 3 3 --hold-margin-ns ${HM:-0.01} ${SM:+--slew-margin-percent $SM}   --sdc-append physical/abi3/v41_w10_elem_pp_multicycle.sdc   --macro-view ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8   --nickname-tag $TAG --keep-workdir $O/work --output $O/physical.json > $O/route.log 2>&1
echo $? > $O/route.exit
