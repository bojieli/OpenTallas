#!/usr/bin/env bash
# TOKd-HBM 10-22: PV ATT_MARK fix. Rebuild ONLY the svg hier block (Vot_hbm_svc_sm_group_rel_id_hw0) from the patched
# m78 master (ATT_MARK=1 in the bench copy), relink the original r18 PV slice objects, compose v4 replay (v2 programme +
# SVG word bit119 on attention issue words, bit25 kept), replay 86000 edges +SHOWVAL, strict acceptance.
set -euo pipefail
R=/srv/opentallas-scratch/claude/tokd-hbm-pv-attmark; P=/srv/opentallas-scratch/claude/hbmc-token2/pv_r18_probe
C=/srv/opentallas-scratch/codex/hbm-pv-calendar-1022
cd $R; ulimit -s unlimited; unset MAKEFLAGS MFLAGS
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
B=Vot_hbm_svc_sm_group_rel_id_hw0
# ---- compose v4 (before the build: fail fast)
if [ ! -f composed_v4/slice/replay/replay_candidate/val.mem ]; then
 mkdir -p composed_v4/slice; cp $P/slice/boundary.json composed_v4/slice/boundary.json
 cp probability_input_plan.json sm_node_scoreboard_candidate.json composed_v4/
 sed -e "s#/srv/opentallas-scratch/codex/hbm-pv-calendar-1022/repo/tools#$R/repo/tools#" \
     -e "s#^r=Path('/srv/opentallas-scratch/codex/hbm-pv-calendar-1022/composed77v3')#r=Path('$R/composed_v4')#" compose77v3.py > compose_v4.py
 grep -q "$R/composed_v4" compose_v4.py; grep -q "$R/repo/tools" compose_v4.py
 python3 compose_v4.py > compose_v4.json
 PYTHONPATH=repo/tools python3 repo/tools/hbm_layer_vehicle/gen_slice_tb.py --boundary composed_v4/slice/boundary.json --out composed_v4/slice --replay composed_v4/replay_candidate.json --nev 5968 > gen_v4.log
 RP="$R/composed_v4/slice/replay/replay_candidate"; cp "$RP/hbm/phy_SW.hex" "$RP/hbm/INIT.hex"
 python3 - "$RP/index.json" <<'PY'
import json,sys
p=sys.argv[1];d=json.load(open(p));d['hbm_preload_sectors']={'INIT':d['hbm_preload_sectors']['phy_SW']};open(p,'w').write(json.dumps(d,indent=1)+'\n')
PY
fi
python3 compare_v4.py > compare_v4.json; cat compare_v4.json | head -12
# ---- rebuild the svg hier block only
mkdir -p obj
if [ ! -f obj/$B/lib${B#V}.a ]; then
 sed "s#$P/out/obj/$B#$R/obj/$B#" $P/out/obj/${B}__hierMkArgs.f > obj/svg_args.f
 grep -q "$R/obj/$B" obj/svg_args.f
 ( cd $R && "$VL" -f obj/svg_args.f ) > obj/verilate.log 2>&1
 # protect-lib guard: the regenerated wrapper must be port-identical to the one the original top was verilated against
 python3 - <<PY
import re
a=open('$P/out/obj/$B/ot_hbm_svc_sm_group_rel_id_hw0.sv').read();b=open('$R/obj/$B/ot_hbm_svc_sm_group_rel_id_hw0.sv').read()
ha=re.search(r"protectlib_hash__V = 32'd(\d+)",a)[1];hb=re.search(r"protectlib_hash__V = 32'd(\d+)",b)[1]
na=a.replace(ha,'H');nb=b.replace(hb,'H')
assert na==nb,'wrapper interface differs'
c='$R/obj/$B/ot_hbm_svc_sm_group_rel_id_hw0.cpp';s=open(c).read();assert s.count(hb+'U')==1;open(c,'w').write(s.replace(hb+'U',ha+'U'))
print('WRAPPER_IDENTICAL orig_hash',ha,'new_hash',hb,'-> lib checks orig hash')
PY
 make -C obj/$B -f $B.mk -j 8 "lib${B#V}.a" > obj/lib.log 2>&1
fi
if [ ! -x obj/Vtb_hbm_slice ]; then
python3 - <<PY
from pathlib import Path
import shutil,subprocess
old=Path('$P/out/obj');p=Path('$R/obj');a=p/'tb_ALL.a';shutil.copy2(old/'Vtb_hbm_slice__ALL.a',a)
names=subprocess.check_output(['ar','t',str(a)],text=True).splitlines()
drop=[n for n in names if n.startswith('$B')];assert drop
subprocess.run(['ar','d',str(a),*drop],check=True)
e=p/'new_objects';shutil.rmtree(e,ignore_errors=True);e.mkdir()
subprocess.run(['ar','x',str(p/'$B/lib${B#V}.a')],cwd=e,check=True)
subprocess.run(['ar','r',str(a),*[str(x) for x in sorted(e.glob('*.o'))]],check=True)
objs=[str(old/n) for n in ['verilated.o','verilated_dpi.o','verilated_timing.o','verilated_threads.o']]
subprocess.run(['g++',*objs,str(a),'-pthread','-lpthread','-latomic','-o',str(p/'Vtb_hbm_slice')],check=True)
PY
 rm -rf obj/new_objects obj/tb_ALL.a
fi
sha256sum obj/Vtb_hbm_slice > binary_v4.sha256
RP="$R/composed_v4/slice/replay/replay_candidate"
/usr/bin/time -v -o v4.time obj/Vtb_hbm_slice +verilator+rand+reset+2 +REPLAY="$RP" +HBM_IMG_DIR="$RP/hbm" +CYCLES=86000 +SHOWVAL > v4.log 2>&1 || true
grep -E 'PV_FAULT_TERMS|SLICE_(PASS|FAIL|SUMMARY|SM_SUMMARY)|protectlib|%Error' v4.log | tail -8
grep -E "SLICE_OUT .*fault" v4.log | grep -v "first=0 last=0" || echo NO_NONZERO_FAULT_OUTPUTS
grep -c "SLICE_CHECK_FAIL" v4.log || true
# strict acceptance (as accept_v3.sh, separate corrected-preload metadata copy only)
python3 - <<'PY'
from pathlib import Path
import shutil,json
src=Path('composed_v4/slice/replay/replay_candidate');dst=Path('receipt_v4')
shutil.copytree(src,dst,dirs_exist_ok=True)
index=dst/'index.json';d=json.loads(index.read_text());d['hbm_preload_sectors']={'phy_SW':136};index.write_text(json.dumps(d,indent=1)+'\n')
for name in ['hdr.mem','val.mem','msk.mem','vm_pre.txt']:assert (src/name).read_bytes()==(dst/name).read_bytes()
PY
python3 repo/tools/hbm_layer_vehicle/check_slice_run.py --replay receipt_v4 --run-log v4.log --boundary $P/slice/boundary.json --tb-source $P/slice/tb_slice.sv --out v4_acceptance.json; echo CHECK_RC=$?
