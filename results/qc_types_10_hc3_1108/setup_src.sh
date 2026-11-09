#!/bin/bash
# QC-TYPES-10/HC3: private cp -al tree of the wave src kw35/src_c303p (hardlinks; files never written) + NEW files
# runtime/asbuilt_hc3.json and (if absent) plan_of_record/plan_qc53v4w.json; bind out seeded with the v4w elaboration
set -e
S=/srv/opentallas-scratch2/claude/kw35/src_c303p; H=/srv/opentallas-scratch2/claude/qct10/hc3; N=$H/src_hc3
rm -rf $H/farm
if [ ! -d $N ]; then cp -al $S $N; fi
Q=physical/die_plan/qwen_compute
chmod u+w $N/$Q/qc_start_1106/runtime $N/$Q/plan_of_record
rm -f $N/$Q/qc_start_1106/runtime/asbuilt_hc3.json; cp $H/asbuilt_hc3.json $N/$Q/qc_start_1106/runtime/asbuilt_hc3.json
[ -e $N/$Q/plan_of_record/plan_qc53v4w.json ] || cp /srv/opentallas-scratch2/claude/qct9/plan_qc53v4w.json $N/$Q/plan_of_record/plan_qc53v4w.json
O=$H/bind_hc3; rm -rf $O; mkdir -p $O
E=/srv/opentallas-scratch2/claude/qct9/reach/bind_v4w
for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json bind_elab_keep.sv die_r56.v provenance_elab.json shim_qfd_dv_slice2.sv; do cp -p $E/$f $O/$f; done
sha256sum $N/$Q/plan_of_record/plan_qc53v4w.json $N/$Q/qc_start_1106/runtime/asbuilt_hc3.json | cut -c1-16
cat > $H/run_bind.sh <<'EOR'
#!/bin/bash
set -u
H=/srv/opentallas-scratch2/claude/qct10/hc3; N=$H/src_hc3; cd $N
P=physical/die_plan/qwen_compute/plan_of_record/plan_qc53v4w.json
A=physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_hc3.json
date; hostname
python3 -B tools/die_plan/bind.py bind $P --out $H/bind_hc3 --strict --asbuilt $A > $H/bind.log 2>&1; echo "BIND rc $?" >> $H/bind.log
date
EOR
chmod +x $H/run_bind.sh
