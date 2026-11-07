#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/s81-bksel-rf7; F=/srv/opentallas-scratch2/claude/s81-bksel-rf6/dsdv_bksel_q_vF; K=$R/dsdv_bksel_q_vG
mkdir -p $K
rsync -a --exclude=/run --exclude=/signoff --exclude=/lec/ --exclude=/views --exclude=/results --exclude=/physical_completion --exclude=__pycache__ --exclude='*.previous.*' --exclude='/lec_async.*' --exclude='/run_*.log' --exclude='/sta_*' --exclude=/image.txt --exclude=/pin_audit.json --exclude=/placed.csv --exclude=/dump_placed.log --exclude='/ot_rt_*' --exclude='/etm_libraries_*' --exclude='/face_guard.json' --exclude='/face_guard_raw.*' --exclude=/reg_fanout.json --exclude=/reg_fanout.log --exclude=/native_cell_count.json --exclude='/orfs_*.log' --exclude='/kit_modes_cts.log' --exclude='/rtl_lint.json' --exclude='/rtl_lint.log' --exclude=/grt_policy --exclude='/grt_policy*.tcl' --exclude='/grt_policy.json' --exclude='/sdc_lint.log' --exclude='/signoff.log' $F/ $K/
cp $F/lec_async.sh $K/lec_async.sh
python3 -I $R/patch_rtl.py gate $K/rtl
python3 -I $R/bank_regs_vg.py $K/bank_regs.tcl
python3 -I - "$K" <<'PY'
import sys,re
k=sys.argv[1]; p=k+'/config.mk'; t=open(p).read()
def one(a,b):
    global t
    assert t.count(a)==1,a
    t=t.replace(a,b)
one('export DESIGN_NICKNAME = kl_dsdv_bksel_q_vD','export DESIGN_NICKNAME = kl_dsdv_bksel_q_vG')
one('-DOT_BKQ_GBREG2\n','-DOT_BKQ_GBREG2 -DOT_BKQ_BSTG -DOT_BKQ_FO8\n')
one('export PLACE_DENSITY = 0.5','export PLACE_DENSITY = 0.40')
one('export OT_RT_MGRP_MAXUM = 0','export OT_RT_MGRP_MAXUM = 60')
one('export OT_HOLD_FF_MARGIN = 0','export OT_HOLD_FF_MARGIN = 20')
t+="\n# ---- S81-BKSEL-RF7 vG 11-07 (OWNER conservative form): bank input stages at the pins, density .40, near-only macro groups, GRT hold margin 20, wider macro channels (macro_place.tcl)\n"
open(p,'w').write(t)
p=k+'/macro_place.tcl'; t=open(p).read()
m=re.search(r'foreach \{master sites\} \{.*\}\} \{\n',t)
assert m
h=[25.92,120.96,216.0,311.04]; s=[406.08,527.04]
big=' '.join('{%g %g R0}'%(x,y) for x in s for y in (43.2,172.8,345.6))
small=' '.join('{%g 216 R0}'%x for x in h)+' {%g 475.2 R0} '%s[0]+' '.join('{%g 345.6 R0}'%x for x in h)+' {%g 475.2 R0}'%s[1]
hist=' '.join('{%g %g R0}'%(x,y) for y in (25.92,120.96) for x in h)+' '+' '.join('{%g %g R0}'%(x,y) for y in (423.36,518.4) for x in h)
new='foreach {master sites} {ot_sram_1r1w_128x256_m1_r2c2_p192_mir {%s} ot_sram_1r1w_32x128_m1_p192_rc {%s} ot_s81ph_native_sel_hist_bank {%s}} {\n'%(big,small,hist)
t=t[:m.start()]+new+t[m.end():]
t='# S81-BKSEL-RF7 vG 11-07: hist columns pitch 95.04 (channel 30.24, was 21.6), hist rows gap 41 (was 32.4), SRAM columns moved E, N band 75.6; all on an 8.64 um grid (M3-M6 track and PG phase unchanged).\n'+t
open(p,'w').write(t)
PY
grep -n -E "NICKNAME|PLACE_DENSITY|MGRP_MAXUM|OT_HOLD_FF_MARGIN|BSTG" $K/config.mk | cut -c1-120
sed -n 1,8p $K/macro_place.tcl | cut -c1-260
ls $K | wc -l; du -sh $K
