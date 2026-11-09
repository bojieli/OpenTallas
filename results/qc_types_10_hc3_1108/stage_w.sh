set -e
H=/srv/opentallas-scratch2/claude/qct10/hc3; N=$H/src_hc3; D=$N/rtl/qwen_sys/dvm_20261014; Q=physical/die_plan/qwen_compute
chmod u+w $D; rm -f $D/ot_qfd_xs_leaf_fo32_w.sv; cp $H/ot_qfd_xs_leaf_fo32_w.sv $D/
rm -f $N/$Q/qc_start_1106/runtime/asbuilt_hc3.json; cp $H/asbuilt_hc3.json $N/$Q/qc_start_1106/runtime/asbuilt_hc3.json
O=$H/bind_hc3; rm -rf $O; mkdir -p $O; E=/srv/opentallas-scratch2/claude/qct9/reach/bind_v4w
for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json bind_elab_keep.sv die_r56.v provenance_elab.json shim_qfd_dv_slice2.sv; do cp -p $E/$f $O/$f; done
rm -f $H/bind.log; md5sum $N/$Q/qc_start_1106/runtime/asbuilt_hc3.json $D/ot_qfd_xs_leaf_fo32_w.sv
