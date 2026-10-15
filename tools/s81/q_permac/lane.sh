#!/bin/bash
set -eu
B=/srv/opentallas-scratch/claude/s81-qpermac; cd $B
IMG=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
python3 - <<'PY'
import json
d=json.load(open('containers.json')); M=d['modules']
old=[k for k in M if 'ot_s81_q_lane_pair_native' in k]; assert len(old)==1,old; old=old[0]
new='ot_s81_q_lane_pair_native_tw17'
M[new]=M.pop(old)
for m in M.values():
    for c in m.get('cells',{}).values():
        if c['type']==old: c['type']=new
json.dump(d,open('containers_ln.json','w'))
print(old,'->',new,{p:(v['direction'],len(v['bits'])) for p,v in M[new]['ports'].items()})
PY
for t in ot_s81_q_lane_pair_native_tw17 ot_s81_q_mac0_native_graph ot_s81_q_mac1_native_graph; do
cat > wv_$t.ys <<YS
read_json $B/containers_ln.json
hierarchy -top $t
check
write_verilog -noattr $B/$t.v
YS
docker run --rm -v $B:$B $IMG /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -s $B/wv_$t.ys > wv_$t.log 2>&1 || { echo WV_FAIL $t; tail -5 wv_$t.log; }
done
grep -c "^module" *.v
