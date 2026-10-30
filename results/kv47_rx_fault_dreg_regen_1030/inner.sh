#!/bin/bash
# DIE-KV-47-HR 10-30: qkd_hr_core_rx regen with KV fault_dreg admission variant; same chain as the RX kit of record
# (hr_face_ports.py face transform -> hr_face_preserve.py v2 keep + retime deferred/fault -> mapped emit).
set -u
cd /r
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
for v in orig dreg; do cat > pre_$v.ys <<YS
read_verilog -defer -sv -DSYNTHESIS src/qkd_hr_core_rx.sv src/adm_$v.sv src/qkd_host_rx_class.sv
hierarchy -top qkd_hr_core_rx
proc
flatten
memory_collect
opt_clean
write_json pre_$v.json
YS
$Y -q -l pre_$v.log pre_$v.ys || { echo PRE_FAIL $v; exit 2; }; done
cp pre_dreg.json pre.json
python3 hr_face_ports.py transform pre.json post.json hr_face_ports.json --top qkd_hr_core_rx || exit 3
python3 hr_face_ports.py transform pre.json mut.json hr_face_ports_mut.json --top qkd_hr_core_rx --mutant >/dev/null || exit 3
python3 hr_face_preserve.py post.json keep.json --top qkd_hr_core_rx --retime-output deferred --retime-output fault > keep_report.json || exit 4
python3 hr_face_preserve.py post.json keepmut.json --top qkd_hr_core_rx --retime-output deferred --retime-output fault --mutant > keepmut_report.json || exit 4
cat > emit.ys <<YS
read_json keep.json
hierarchy -top qkd_hr_core_rx
memory_share
memory_map
opt_clean
write_verilog keep_mapped.v
YS
$Y -q -l emit.log emit.ys || exit 5
hdr_json(){ printf "read_json %s\nmemory_share\nmemory_map\nrename qkd_hr_core_rx gold\ndesign -stash g\n" "$1"; }
tail_eq(){ printf "rename qkd_hr_core_rx gate\ndesign -copy-from g -as gold gold\nequiv_make gold gate eq\nhierarchy -top eq\nexpose -evert eq/t:ot_sram*\nasync2sync\nequiv_simple -seq 2\nequiv_induct -seq 2\nequiv_status %s\n" "$1"; }
flat="setattr -mod -unset keep_hierarchy\nsetattr -unset keep_hierarchy\nflatten\n"
{ hdr_json old_pre.json; printf "read_json pre_orig.json\nmemory_share\nmemory_map\n"; tail_eq -assert; } > eq_id.ys
{ hdr_json pre.json; printf "read_json post.json\nmemory_share\nmemory_map\n"; tail_eq -assert; } > eq_post.ys
{ hdr_json pre.json; printf "read_json mut.json\nmemory_share\nmemory_map\n"; tail_eq -assert; } > eq_mut.ys
{ hdr_json post.json; printf "read_json keep.json\nhierarchy -top qkd_hr_core_rx\n$flat memory_share\nmemory_map\n"; tail_eq -assert; } > eq_keep.ys
{ hdr_json post.json; printf "read_json keepmut.json\nhierarchy -top qkd_hr_core_rx\n$flat memory_share\nmemory_map\n"; tail_eq -assert; } > eq_keepmut.ys
{ hdr_json post.json; printf "read_verilog -sv keep_mapped.v\nhierarchy -top qkd_hr_core_rx\nproc\n$flat memory_share\nmemory_map\n"; tail_eq -assert; } > eq_v.ys
# new kit RTL vs RTL of record (old kit rtl): intended difference = host_d/ing_d/ing_cls data regs only
printf "read_verilog -sv old_kit_rtl.v\nhierarchy -top qkd_hr_core_rx\nproc\n$flat memory_share\nmemory_map\nrename qkd_hr_core_rx gold\ndesign -stash g\nread_verilog -sv keep_mapped.v\nhierarchy -top qkd_hr_core_rx\nproc\n$flat memory_share\nmemory_map\n" > eq_rec.ys; tail_eq "" >> eq_rec.ys; echo "equiv_status -undef" >> eq_rec.ys
for v in id post mut keep keepmut v rec; do ( $Y -q -l eq_$v.log eq_$v.ys >/dev/null 2>&1; echo "$v rc=$?" >> eq_rc.txt ) & done
wait
sort eq_rc.txt
