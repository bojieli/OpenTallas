from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-s81-rck-0222/work')
s=(R/'results/s81_rck_11_reform_1108/tx_pilot/make_tx_pilot.py').read_text()
s=s.replace('tx_pilot','tx_feedback').replace('W,H=181.44,172.8','W,H=181.44,181.44').replace('rck_tx_181x155_0222.json','rck_tx_feedback_181_0222.json')
s=s.replace("suffix='vA',clock_pin_um=[W/2,H/2]", "suffix='vD_region',orfs_vars=dict(OT_SKIP_PRECTS_METRICS=1,PRE_GLOBAL_PLACE_TCL='/work/feedback_pre_gpl.tcl',PRE_DETAIL_PLACE_TCL='/work/feedback_pre_dpl.tcl')")
exec(compile(s,'make_tx_feedback_profile','exec'))
