W=/srv/opentallas-scratch2/claude/qc-event-s25/gate; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime; G=/srv/opentallas-scratch2/claude/dq97/taps1111/bind_gr
P=plan_qc99_s25; S=$W/src_s25; PL=$W/planq/$P.json; O=$W/bind_$P
echo "bind3 start $(date) plan=$(sha256sum $PL|cut -c1-12) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) r8=$(sha256sum $S/$RT/r8_sw2.json|cut -c1-12)" > $W/bind_$P.log
rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $W/bind_$P.log 2>&1
echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $W/bind_$P.log
