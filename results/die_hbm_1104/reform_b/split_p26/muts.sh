#!/bin/bash
# (B exported: the first wave ran unmutated because m_*.sed resolved to /m_*.sed)
# seam mutants + OPEN_IL=1, 8 at a time; every mutant must FAIL, il1 must PASS.  Result lines go to out/muts.txt
B=/srv/opentallas-scratch3/claude/hbm-reform-b5/bench; cd $B; export B VL_JOBS=8
run(){ n=$1; case $n in
 ps*) m=${n#ps}; echo "s/^module ot_svgr_prod_s #(\(.*\)parameter integer MUT=0)(/module ot_svgr_prod_s #(\1parameter integer MUT=$m)(/" > m_$n.sed;;
 ow*) m=${n#ow}; echo "/^module ot_svgr_own #(/s/parameter integer MUT=0)(/parameter integer MUT=$m)(/" > m_$n.sed;;
 il1) : > m_$n.sed;; esac
 bash mkbench.sh $n $B/m_$n.sed > out/$n.mk 2>&1
 [ $n = il1 ] && { TB=rtl/test/hbm_accel/svg_rel/tb_hbm_svg_rel_sm.sv; sed 's/\.PREL(1),\.DD(256),\.IMUT/.PREL(1),.DD(256),.OPEN_IL(1),.IMUT/' src_il1/$TB > src_il1/$TB.n; rm -f src_il1/$TB; mv src_il1/$TB.n src_il1/$TB; grep -c 'OPEN_IL(1)' src_il1/$TB >> out/il1.mk; }
 bash one.sh $n L00:0 smoke > out/$n.log 2>&1
 G=rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_group_rel_id.sv
 echo "$n tree=$(tail -1 out/$n.mk | cut -c1-20) mutparam=$(grep -cE 'MUT=[1-4]\)\(' src_$n/$G) il=$(grep -c 'OPEN_IL(1)' src_$n/rtl/test/hbm_accel/svg_rel/tb_hbm_svg_rel_sm.sv) $(grep -m1 -E 'SMB_UNIT|FAULT|Error' out/$n.smoke.log | cut -c1-120)" >> out/muts.txt
 rm -rf work_$n/obj_*; }
export -f run; printf '%s\n' il1 ps1 ps2 ps3 ow1 ow2 ow3 ow4 | xargs -P 8 -I{} bash -c 'run {}'
echo ALLDONE >> out/muts.txt
