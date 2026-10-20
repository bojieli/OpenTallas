#!/bin/bash
# OWN-QWEN/KV-PARENTS trial 2: as trial 1 but kv_expand + pvw_die_t RTL + result-trunk / ctl_t views from main c402cb103
# (overlay tree: real dirs only for the overlaid paths, everything else symlinked READ-ONLY to the kvs14p source tree).
set -u
R=/srv/opentallas-scratch/claude/qwen-kvsys/kvs14p-fa7fe4ff9
P=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14p-fa7fe4ff9
B=/srv/opentallas-scratch/claude/ownq-kvpar
T=$B/src_overlay; O=$B/pvw_expand_trial2
rm -rf $T $O; mkdir -p $T $O
lnall() { local src=$1 dst=$2; shift 2; mkdir -p $dst; for e in $src/* $src/.[!.]*; do [ -e "$e" ] || continue; n=$(basename $e); case " $* " in *" $n "*) mkdir -p $dst/$n;; *) ln -s $e $dst/$n;; esac; done; }
lnall $P $T tools rtl physical
lnall $P/tools $T/tools qwen_kv_die
lnall $P/rtl $T/rtl qwen_sys hdc
lnall $P/rtl/qwen_sys $T/rtl/qwen_sys split_20261014
lnall $P/rtl/hdc $T/rtl/hdc nearhbm
lnall $P/physical $T/physical ref_tile
lnall $P/physical/ref_tile $T/physical/ref_tile qkd_rlyi_258s qkd_pv_rs_hd_r qkd_rlyi_258 qkd_pv_rs_hd qkd_pv_ctl_t_d54f58a95
lnall $P/tools/qwen_kv_die $T/tools/qwen_kv_die kv_expand.py; rmdir $T/tools/qwen_kv_die/kv_expand.py
lnall $P/rtl/qwen_sys/split_20261014 $T/rtl/qwen_sys/split_20261014 qkd_pvw_die_t.sv qkd_pv_rtrunk.sv; rmdir $T/rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv $T/rtl/qwen_sys/split_20261014/qkd_pv_rtrunk.sv
rmdir $T/rtl/hdc/nearhbm; ln -s $P/rtl/hdc/nearhbm $T/rtl/hdc/nearhbm
mkdir -p $B/ov; rm -rf $B/ov/*; tar -xzf $B/main_overlay.tgz -C $B/ov
cp $B/ov/tools/qwen_kv_die/kv_expand.py $T/tools/qwen_kv_die/; cp $B/ov/rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv $B/ov/rtl/qwen_sys/split_20261014/qkd_pv_rtrunk.sv $T/rtl/qwen_sys/split_20261014/
for k in qkd_rlyi_258s qkd_pv_rs_hd_r qkd_rlyi_258 qkd_pv_rs_hd qkd_pv_ctl_t_d54f58a95; do rmdir $T/physical/ref_tile/$k; cp -a $B/ov/physical/ref_tile/$k $T/physical/ref_tile/; done
cp -a $R/case_kv $R/libs $R/kv_flags.env $O/
for f in $R/*.json; do cp -a $f $O/; done; rm -f $O/expand.json $O/static_bind.json
cd $T || exit 2
export PYTHONDONTWRITEBYTECODE=1
set -a; . $O/kv_flags.env; set +a
export OT_KV_PV_T_CTL_KIT=qkd_pv_ctl_t_d54f58a95
echo "TRIAL2 start $(date) overlay=plan5 tools + main kv_expand.py/qkd_pvw_die_t.sv/qkd_pv_rtrunk.sv/5 views c402cb103 CTL_KIT=$OT_KV_PV_T_CTL_KIT"
python3 tools/qwen_kv_die/kv_expand.py --run $O --only qkd_pvw_s,qkd_pvw_n > $O/expand_pvw.log 2>&1; rc=$?
echo "EXPAND rc=$rc"; tail -30 $O/expand_pvw.log
python3 - $O <<'PY'
import json,sys,os
p=os.path.join(sys.argv[1],'expand.json')
if os.path.exists(p):
    d=json.load(open(p)); print('EXPAND_JSON', {k:(len(v) if isinstance(v,(list,dict)) else v) for k,v in d.items()})
    print('standin', json.dumps(d.get('standin'))[:400]); print('frames', json.dumps(d.get('frames'))[:1500])
    lv=d.get('leaves'); print('leaves', json.dumps(lv)[:1500])
PY
