#!/bin/bash
# mkbench_hg8.sh NAME RTLDIR [FSPARAMS] [SEDFILE...]: bench tree src_NAME from HBM-GAPS-5 src_rf1 with the svgr_top/feed/producer
# modules from RTLDIR/ot_svgr_top_cachecut.sv (renamed, _cachecut stripped), RTLDIR cache136 + issuer; FSPARAMS = parameter list for u_fcore.
set -e; N=$1; R=$2; P=${3:-}; shift 3 || shift $#
B=/srv/opentallas-scratch3/claude/hbm-gaps-8/bench; S0=/srv/opentallas-scratch2/claude/hbm-gaps-5-lec/bench/src_rf1
rm -rf $B/src_$N; cp -a $S0 $B/src_$N; T=$B/tmp_$N; rm -rf $T; mkdir -p $T
D=rtl/hbm_accel/loader/service_native; G=$D/ot_hbm_svc_sm_group_rel_id.sv
cp $R/ot_svgr_top_cachecut.sv $R/ot_svgr_cache136_native.sv $R/ot_hbm_svc_sm_issuer_rel.sv $T/
for s in "$@"; do for f in $T/*.sv; do sed -i -f "$s" $f; done; done
sed 's/_cachecut//g' $T/ot_svgr_top_cachecut.sv | awk '/^module ot_svgr_k_out /{exit} {print}' | sed '1,/^module ot_svgr_top /{/^module ot_svgr_top /!d}' > $T/top.sv
grep -q '^module ot_svgr_top ' $T/top.sv
{ sed -n '1,54p' $S0/$G; cat $T/top.sv; awk '/^module ot_svgr_k_out /{p=1} p' $S0/$G; } > $T/group.sv
[ -n "$P" ] && sed -i "s/^    ot_svgr_top u_fcore (/    ot_svgr_top #($P) u_fcore (/" $T/group.sv
rm -f $B/src_$N/$G; cp $T/group.sv $B/src_$N/$G
rm -f $B/src_$N/$D/ot_hbm_svc_sm_issuer_rel.sv; cp $T/ot_hbm_svc_sm_issuer_rel.sv $B/src_$N/$D/
cp $T/ot_svgr_cache136_native.sv $B/src_$N/$D/
F=tools/hbm_layer_vehicle/smb_svc_files.txt; { cat $S0/$F; echo; echo $D/ot_svgr_cache136_native.sv; } > $T/f.txt; rm -f $B/src_$N/$F; cp $T/f.txt $B/src_$N/$F
echo "tree $N ok params=[$P] fcore=$(grep -c 'ot_svgr_top #(' $B/src_$N/$G) p1=$(grep -c 'P1' $B/src_$N/$G)"
