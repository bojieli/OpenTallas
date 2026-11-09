C=/srv/opentallas-scratch2/claude/codex-head-ctl-1113; W=/srv/opentallas-scratch2/claude/dh88/lep; SRC=$C/lep_source
rm -rf $W/prepared_dt
cd $SRC/tools/s81_head; PYTHONPATH=$W/pylib timeout 900 python3 head_rf_prepare.py /srv/opentallas-scratch3/claude/kw23/prep_l48ui $W/event_dt $W/prepared_dt --tools $SRC --types hd_lep0N --event lep_dt_1108 2>&1 | tail -3 | cut -c1-400
python3 -I -c "
import json;d=json.load(open('$W/prepared_dt/source_plan.json'));c=d['partition_types']['hd_lep0N']['clock'];print(c.get('tap_mode'),c.get('tap_radius_um'),c.get('tap_target_sinks'))"
bash /tmp/lep_gen_x.sh
