#!/bin/bash
# S81-BKSEL-RF7 proof: yosys equiv of reference (vD + plain 2-edge delay on all bank inputs and t_s control) vs vG, real hist_bank RTL, SRAM blackbox; mutants must fail.
E=/srv/opentallas-scratch2/claude/s81-bksel-rf7/eqv
cd $E
scp -q -o ControlPath=none epyc4:/srv/opentallas-scratch3/claude/s81-bksel-rf5/eqv/eq_pass.ys tmpl.ys
python3 -I - <<'PY'
import re
t=open('tmpl.ys').read()
g=t.index('design -stash gold')
gold=t[:g].replace('-DOT_BKQ_GBREG ','-DOT_BKQ_GBREG -DOT_BKQ_GBREG2 ')
rest=t[g:]
rest=rest.replace('-DOT_BKQ_GBREG2 ','-DOT_BKQ_GBREG2 -DOT_BKQ_BSTG -DOT_BKQ_FO8 @M@')
rest=rest.replace('equiv_make -blacklist /e/blacklist.txt gold gate eq','equiv_make gold gate eq')
for name,d in [('pass',''),('dg','-DOT_BKQ_BSTG_MUT_DG '),('rn','-DOT_BKQ_BSTG_MUT_RN '),('g','-DOT_BKQ_BSTG_MUT_G '),('ctl','-DOT_BKQ_BSTG_MUT_CTL ')]:
    s=gold+rest.replace('@M@',d).replace('eq_pass_status',f'eq_{name}_status')
    open(f'eq_{name}.ys','w').write(s)
PY
pids=
for n in pass dg rn g ctl; do
  ( docker run --rm -m 12g --cpus 2 --name bkrf7-eq-$n -v $E:/e -w /e openroad/orfs:asap7lock bash -c "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l /e/eq_$n.log -s /e/eq_$n.ys" > eq_$n.out 2>&1; echo $? > eq_$n.rc ) &
done
wait; echo EQ_ALL_DONE $(date -Is); for n in pass dg rn g ctl; do echo $n rc $(cat eq_$n.rc) $(tail -2 eq_${n}_status.txt 2>/dev/null | tr '\n' ' '); done
