#!/bin/bash
# DIE-KV-47-HR core_tx RTL regen (Codex tx_current recipe; mu = KV-only hr_tx_predecode variant, wrapper CONST_LANE_WRITES=1)
set -eu
cd /work
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
cat > pre.ys <<YS
read_verilog -defer -sv -DSYNTHESIS source/qkd_hr_core_tx.sv source/qkd_host_tx_class.sv source/qkd_host_axi_packet.sv source/qkd_host_ctrl_token_service_packet_collected.sv source/qkd_host_ctrl_token_service_packet_collected_mu.sv
hierarchy -top qkd_hr_core_tx
proc
flatten
memory_collect
opt_clean
write_json pre.json
YS
$Y -q -l pre.log pre.ys
for v in post mut; do
 extra=; [ "$v" = mut ] && extra=--mutant
 python3 hr_face_ports.py transform pre.json $v.json hr_face_ports_$v.json --top qkd_hr_core_tx --retime-in "u_ctrl__package_abort[0]" $extra
done
cp hr_face_ports_post.json hr_face_ports.json
printf "read_json post.json\nwrite_verilog qkd_hr_core_tx.v\n" > emit.ys
$Y -q -l emit.log emit.ys
python3 - <<PY
import re
from pathlib import Path
p=Path("qkd_hr_core_tx.v");s=p.read_text();s=re.sub(r"\(\* src = \"[^\"]*\" \*\)\s*","",s);p.write_text(s)
rd={"post":"read_json post.json","mut":"read_json mut.json",
 "v":"read_verilog -sv qkd_hr_core_tx.v\nhierarchy -top qkd_hr_core_tx\nproc\nmemory_collect\nrename -hide w:_*_\nopt_clean"}
for v,gate in rd.items():
 Path(f"eq_{v}.ys").write_text(f"read_json pre.json\nmemory_share\nmemory_map\nrename qkd_hr_core_tx gold\ndesign -stash g\n{gate}\nmemory_share\nmemory_map\nrename qkd_hr_core_tx gate\ndesign -copy-from g -as gold gold\nequiv_make gold gate eq\nhierarchy -top eq\nasync2sync\nequiv_simple -seq 2\nequiv_induct -seq 2\nequiv_status -assert\n")
# LEC vs RTL of record (kv-kits-15 kit rtl, ba6778f278fa): report proven/unproven, no assert
Path("eq_rec.ys").write_text("read_verilog -sv rec_of_record.v\nhierarchy -top qkd_hr_core_tx\nproc\nmemory_collect\nrename -hide w:_*_\nopt_clean\nmemory_share\nmemory_map\nrename qkd_hr_core_tx gold\ndesign -stash g\nread_verilog -sv qkd_hr_core_tx.v\nhierarchy -top qkd_hr_core_tx\nproc\nmemory_collect\nrename -hide w:_*_\nopt_clean\nmemory_share\nmemory_map\nrename qkd_hr_core_tx gate\ndesign -copy-from g -as gold gold\nequiv_make gold gate eq\nhierarchy -top eq\nasync2sync\nequiv_simple -seq 2\nequiv_induct -seq 2\nequiv_status\n")
PY
for v in post mut v rec; do
 (set +e; $Y -q -l eq_$v.log eq_$v.ys > eq_$v.stdout 2>&1; echo $? > rc_$v) &
done
wait
printf "post rc=%s\nmut rc=%s\nemitted_v rc=%s\nrec rc=%s\n" "$(cat rc_post)" "$(cat rc_mut)" "$(cat rc_v)" "$(cat rc_rec)" | tee eq_rc.txt
