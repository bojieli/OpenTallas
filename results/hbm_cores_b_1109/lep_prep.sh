C=/srv/opentallas-scratch2/claude/codex-head-ctl-1113; W=/srv/opentallas-scratch2/claude/dh88/lep; SRC=$C/lep_source
tail -1 $W/event_dt.log | cut -c1-300
cd $SRC/tools/s81_head; PYTHONPATH=$W/pylib timeout 900 python3 head_rf_prepare.py /srv/opentallas-scratch3/claude/kw23/prep_l48ui $W/event_dt $W/prepared_dt --tools $SRC --types hd_lep0N --event lep_dt_1108 2>&1 | tail -3 | cut -c1-400
ls $W/prepared_dt | head -30 | tr '\n' ' '
cd $SRC; python3 tools/die_plan/gen.py phys --help 2>&1 | head -40 | cut -c1-200
