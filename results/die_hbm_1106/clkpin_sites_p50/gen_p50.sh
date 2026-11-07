#!/bin/bash
# gen_p50.sh WT OUT : --clock-pin-entry on kits of the part-50 modules from the base and new plans
W=$1; O=$2; G=$W/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py
for d in base new; do
  python3 -I -c "
import json,ast
for x in json.load(open('$O/views_$d.json'))['view_list']:
    if x['module'] in ('ot_hbm_idx_qctl_static','ot_hbm_static_cfg_collar_idx256r','ot_pdie_serdes_rx_bm3_rest'):
        rk=x['recipe_keys']; rk=ast.literal_eval(rk) if isinstance(rk,str) else rk
        print(x['view'], rk[0] if rk else '-')" | while read view rk; do
    tag=${view//@/_}; mkdir -p $O/kits_$d/$tag; extra=""; [ "$rk" != "-" ] && extra="--recipe-key $rk"
    ( cd $W && timeout 1500 prlimit --as=24000000000 python3 -I -c "import runpy,sys;sys.path[:0]=['$W/physical/die_plan/hbm_arch_cores','$W/tools/die_plan'];sys.argv=['$G']+sys.argv[1:];runpy.run_path('$G',run_name='__main__')" --views $O/views_$d.json --view $view $extra --out $O/kits_$d/$tag --clock-pin-entry on --core-macros auto > $O/kits_$d/$tag.log 2>&1; echo "$d $view rc=$?" ) &
  done
done; wait; echo GEN_DONE
