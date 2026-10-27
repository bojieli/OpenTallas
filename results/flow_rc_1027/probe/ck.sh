# ck.sh <tag> <signoff_dir>: clock-sink arrival est (current/T1/T2) vs RCX, TT
W=/srv/opentallas-scratch2/claude/flow-rc-1027; T=$W/tools; O=$W/$1/ck; SO=$2/tt; mkdir -p $O/rc; cp $T/setRC_rcx_asap7.tcl $T/frc_T1.tcl $T/frc_T2.tcl $O/rc/
S=$SO/session.tcl; n=$(grep -n "^read_db" $S | head -1 | cut -d: -f1)
{ head -n $((n-1)) $S | sed "s#^read_db.*##"; cat $T/ckbody.tcl; } > $O/ck.tcl
# rc_calib_probe reads the db itself: drop duplicate read_db from the head (already cut), keep lib loading
mounts=$(grep -o -- "-v [^ ]*" $SO/cmd.sh | grep -v ":/out$" | tr "\n" " ")
for m in rcx est; do
 docker run --rm --memory 24g $mounts -v $O:/out -e OT_MODE=$m -e OT_ODB=$([ $m = rcx ] && echo /base/6_final.odb || echo /base/5_1_grt.odb) -e OT_SPEF=/base/6_final.spef -e OT_SDC=/sdc/golden.sdc -e OT_LAYERS=M2-M5 -e "OT_RC_FILES=/out/rc/setRC_rcx_asap7.tcl /out/rc/frc_T1.tcl /out/rc/frc_T2.tcl" -e OT_OUT=/out/tt_$m openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/ck.tcl > $O/$m.log 2>&1 &
done; wait
cd $O; for e in tt_est_setRC_rcx_asap7 tt_est_frc_T1 tt_est_frc_T2; do echo "$e $(python3 $T/rc_calib.py cmp --ref tt_rcx_rcx.tsv --est $e.tsv)"; done > cmp.txt; echo CKDONE >> cmp.txt
