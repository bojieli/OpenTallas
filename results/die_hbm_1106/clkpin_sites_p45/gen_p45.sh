#!/bin/bash
# DIE-HBM-82 part 45 proof: one --clock-pin-entry on kit per p35 core, on main (base) and on part 45 (new) plan copies.
# usage: gen_p45.sh WT R   (R holds plan_{base,new}/ unzipped + views_{base,new}.json)
W=$1; R=$2
G=$W/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py
gen() { # N mod
  local N=$1 mod=$2
  local view=$(python3 -I -c "import json,sys;print([x['view'] for x in json.load(open('$R/views_$N.json'))['view_list'] if x['module']=='$mod'][0])")
  mkdir -p $R/kits_$N/$mod
  ( cd $W && timeout 3000 prlimit --as=48000000000 python3 -I -c "import runpy,sys;sys.path[:0]=['$W/physical/die_plan/hbm_arch_cores','$W/tools/die_plan'];sys.argv=['$G']+sys.argv[1:];runpy.run_path('$G',run_name='__main__')" --views $R/views_$N.json --view $view --recipe-key $mod \
     --out $R/kits_$N/$mod --clock-pin-entry on --core-macros auto > $R/gen_${N}_$mod.log 2>&1; echo "GEN $N $mod $view rc=$?" )
}
for N in base new; do for m in ot_hbm_svc_vm_kshare_splitstrap__v8e478a ot_hbm_svc_vm_kshare_splitstrap__v700685 ot_hgi_sm_xload_cl2_ctlx ot_svgr_bk ot_wbq_root ot_wbq_sw; do gen $N $m & done; done; wait
