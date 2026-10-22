#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

base=Path('/srv/opentallas-scratch/claude/toksim-s81d-wqbp')
model=base/'runs/l0_p126/model'
source=base/'root/tools'
files=[model/'contract.json',model/'source_ctl.txt',base/'root/sid6_fixture/meta.json',
       base/'wqbp_golden_check.py',source/'hdc_golden_v41.py',source/'hdc_golden.py',
       source/'s81_slice/cap_model.py',source/'s81_dv/frame_return_plan.py',
       source/'s81_dv/layer_prog/qf_producer/head_local_contract.py',
       source/'s81_dv/layer_prog/xs_calendar.py']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
log=Path('candidate/diagnostic.log').read_text()
def times(kind):
    return [int(x) for x in re.findall(r'^'+kind+r' t=(\d+)',log,re.M)]
frame,cw,vp=map(times,['FRAME_RETURN','ACTUAL_CW','VP_ACTUAL_COMMIT'])
# VP raw-source writes precede capture; take only actual CW-active commits.
vp=[int(x) for x in re.findall(r'^VP_ACTUAL_COMMIT t=(\d+).* cwv=(?!00)[01]+ collision=0$',log,re.M)]
receipt=dict(scope='CAP capture calibration only; no consumer runtime retirement/deadline qualification',
             full_stage_qualified=False,source_hashes=hashes,
             first_frame_return=min(frame),last_frame_return=max(frame),
             first_cw=min(cw),last_cw=max(cw),first_vp_capture=min(vp),last_vp_capture=max(vp),
             measured_frame_to_last_vp=max(vp)-max(frame),
             priced_tail=195,priced_tail_slack_diagnostic=max(frame)+195-max(vp),
             priced_tail_is_consumer_deadline_proof=False,
             descriptor_commands=15,added_hardware_edges=0,
             qualification=json.loads(Path('capture_qualification.json').read_text()))
Path('receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('source_hashes','qualification')},indent=2))
