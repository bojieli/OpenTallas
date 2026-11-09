set -x
C=/srv/opentallas-scratch2/claude/codex-head-ctl-1113; W=/srv/opentallas-scratch2/claude/dh88/lep; SRC=$C/lep_source
cd $SRC
rm -rf $W/kit_rtl_out $W/gen
TYPE=hd_lep0N OUT=$W/kit_rtl_out PLAN=$W/prepared_dt/source_plan.json bash $W/kit_rtl.sh 2>&1 | tail -3
ls $W/kit_rtl_out | head; 
FL=$(ls $W/kit_rtl_out/kit_rtl*.f $W/kit_rtl_out/*.f 2>/dev/null | head -1); echo FL=$FL
export OT_FLOW_TAG=flow-20261108-ef-head OT_IO_HOLD=sender_min
python3 tools/die_plan/gen.py phys $W/prepared_dt/source_plan.json --types hd_lep0N --out $W/gen --kit-rtl hd_lep0N=$FL --clock-landing $W/prepared_dt/source_sidecar.json --hold-ff-margin 10 --max-wire-um 80 --cland-pinslot all 2>&1 | tail -6 | cut -c1-300
ls $W/gen/hd_lep0N 2>/dev/null | wc -l; du -sh $W/gen
