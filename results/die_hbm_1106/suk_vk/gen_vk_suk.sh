#!/bin/bash
# gen_vk_suk.sh exp|full : generates the vK kit from the part55 plan, swaps in ALAT 6 RTL, adds hold scope.
set -e
R=/srv/opentallas-scratch2/claude/hbm-cons-2-suk; S=$R/repo; PL=$R/rr/new
case $1 in exp) M=ot_hbm_su_pg_lane_exp_x_core; DS=${2:-0.56};; full) M=ot_hbm_su_pg_lane_full_x_core; DS=${2:-0.56};; esac
python3 -I - "$PL" "$M" "$R/views_k.json" <<'P'
import json,sys,hashlib,os
pl,m,out=sys.argv[1:]
if os.path.exists(out): V=json.load(open(out))
else: V=json.load(open("/srv/opentallas-scratch2/claude/hbm-cons-2/views/views_7281a.json"))
V["plan"]=pl+"/die_plan.json"; V["plan_sha256"]=hashlib.sha256(open(V["plan"],"rb").read()).hexdigest()
for r in V["view_list"]:
    if r["module"]==m:
        W={"ot_hbm_su_pg_lane_exp_x_core":328.32,"ot_hbm_su_pg_lane_full_x_core":371.52}[m]
        pf="cores/%s__%gx207.36__d44v_p55.json"%(m,W); sh=hashlib.sha256(open(pl+"/"+pf,"rb").read()).hexdigest()
        r.update(outline_um=[W,207.36],pins_file=pf,pins_sha256=sh,view=m+"@"+sh[:12]); print(r["view"])
json.dump(V,open(out,"w"))
P
VIEW=$(python3 -I -c "import json,sys;print([r['view'] for r in json.load(open('$R/views_k.json'))['view_list'] if r['module']=='$M'][0])")
SH=${VIEW#*@}; OUT=$R/kits/${M}_${SH}_vK; rm -rf $OUT; mkdir -p $OUT $R/logs
cd $S && prlimit --as=48000000000 python3 physical/die_plan/hbm_arch_cores/gen_core_kit_hbm_rw.py --views $R/views_k.json --view "$VIEW" --out $OUT --clock-pin-entry on --core-macros auto --util 0.40 --max-fanout 8 --sigmax M6 --face-reset-relay 2 --clock-regions $PL/core_clock_regions.json --tag _vK > $R/logs/gen_${M}.log 2>&1
K=$(dirname $(ls -d $OUT/*/freeze.json)); echo KIT $K
G=$R/gen_xk
cp $G/ot_hbm_su_static_lane_xb.sv $G/ot_hbm_su_static_lane_pinreg_xb.sv $K/rtl/
sed "s/^module $M #(/module ${M}__mc #(/" $G/$M.sv > $K/rtl/$M.sv; grep -q "^module ${M}__mc #(" $K/rtl/$M.sv
python3 -I - $K/config.mk <<'P'
import sys,re
p=sys.argv[1]; t=open(p).read()
a,b=t.count("/work/rtl/ot_hbm_su_static_lane_x.sv"),t.count("/work/rtl/ot_hbm_su_static_lane_pinreg_x.sv")
assert a==1 and b==1,(a,b)
t=t.replace("/work/rtl/ot_hbm_su_static_lane_x.sv","/work/rtl/ot_hbm_su_static_lane_xb.sv").replace("/work/rtl/ot_hbm_su_static_lane_pinreg_x.sv","/work/rtl/ot_hbm_su_static_lane_pinreg_xb.sv")
open(p,"w").write(t)
P
cat >> $K/config.mk <<CFG

# HBM-CONS-2/SUK 11-06: vK = PART 55 edge columns, ALAT 6 RTL (results/die_hbm_1106/suk_vk/gen_lane_xk.py), plain tree, NO latbal.
export OT_HOLD_REPAIR_SCOPE = reg2reg
export OT_HOLD_STOP = grt:6000
override export PLACE_DENSITY = $DS
CFG
grep -c sux_latbal $K/post_cts_setup.tcl $K/config.mk || true
ls $K/rtl | wc -l
grep -n "^module " $K/rtl/$M.sv | head -3
grep -n "PLACE_DENSITY\|DIE_AREA\|CORE_AREA\|MAX_ROUTING\|POST_CTS_TCL\|PRE_CTS_TCL" $K/config.mk | cut -c1-110
cut -c1-100 $K/macro_placement.tcl
python3 -I - $K $M <<'P'
import json,sys
k,m=sys.argv[1:]
c=json.load(open(k+"/core.json")); print({x:c[x] for x in c if x in ("outline_um","obs_max","clock_entry")})
P
grep -n "clk" $K/io.tcl | head -3 | cut -c1-140
