W=/srv/opentallas-scratch2/claude/qc-event-s25/gate; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
P=plan_qc99_s25; S=$W/src_s25; O=$W/bind_$P
echo "verify start $(date) plan=$(sha256sum $W/planq/$P.json|cut -c1-12) bind_dir=$O" > $W/verify_$P.log
s=$(date +%s); cd $S && timeout -s ABRT 43200 nice -n 19 python3 -I -X faulthandler tools/die_plan/bind.py verify $W/planq/$P.json --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict --mem 96 >> $W/verify_$P.log 2>&1
echo "VERIFY_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $W/verify_$P.log
