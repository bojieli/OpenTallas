#!/bin/bash
# paths.sh <orfs_dir> [N] [ss|ff] [macro dirs...]: the N worst endpoints (one path each) at the corner, start -> end slack
o=$1; N=${2:-60}; c=${3:-ss}; shift 3 2>/dev/null
P=/OpenROAD-flow-scripts/flow/platforms/asap7
if [ $c = ss ]; then L="AO_RVT_SS_nldm_211120.lib.gz INVBUF_RVT_SS_nldm_220122.lib.gz OA_RVT_SS_nldm_211120.lib.gz SEQ_RVT_SS_nldm_220123.lib SIMPLE_RVT_SS_nldm_211120.lib.gz"; k=max
else L="AO_RVT_FF_nldm_211120.lib.gz INVBUF_RVT_FF_nldm_220122.lib.gz OA_RVT_FF_nldm_211120.lib.gz SEQ_RVT_FF_nldm_220123.lib SIMPLE_RVT_FF_nldm_211120.lib.gz"; k=min; fi
base=$(cd $o && ls -d results/asap7/*/base | head -1)
{ echo "read_lef $P/lef/asap7_tech_1x_201209.lef"; echo "read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef"
  for m in "$@"; do echo "read_lef /m/$(basename $m)/$(basename $m).lef"; echo "read_liberty /m/$(basename $m)/$(basename $m)_$c.lib"; done
  for l in $L; do echo "read_liberty $P/lib/NLDM/asap7sc7p5t_$l"; done
  echo "read_db /work/$base/6_final.odb"; echo "read_sdc /work/$base/6_final.sdc"; echo "read_spef /work/$base/6_final.spef"
  echo "set_propagated_clock [all_clocks]"
  echo "foreach p [find_timing_paths -path_delay $k -group_path_count $N -endpoint_path_count 1] { puts \"PATH [format %.1f [get_property \$p slack]] [get_full_name [get_property \$p startpoint]] -> [get_full_name [get_property \$p endpoint]]\" }"
  echo exit; } > $o/qc_paths_$c.tcl
MV=""; for m in "$@"; do MV="$MV -v $(readlink -f $m):/m/$(basename $m):ro"; done
docker run --rm -v $(readlink -f $o):/work $MV openroad/orfs:latest bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/qc_paths_$c.tcl" 2>&1 | grep '^PATH'
