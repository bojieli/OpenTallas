#!/usr/bin/env python3
"""Matched nominal and causal negative admission for CAP capture ONLY."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

root=Path('/srv/opentallas-scratch/claude/toksim-s81d-wqbp/root')
checker='/srv/opentallas-scratch/claude/toksim-s81d-wqbp/wqbp_golden_check.py'
rows=[]
reference=None
for name,expected_pass,cause in [('candidate',True,0),('wrong_rbase',False,0x100),('late_cfg',False,0x400)]:
    run=Path(name)
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((run/'images').glob('*.viamap.hex'))}
    if reference is None: reference=manifest
    assert manifest==reference, f'Unmatched nominal images: {name}'
    rc=subprocess.run([sys.executable,'check_fullsix_cap_capture.py',str(root),str(root/'sid6_fixture'),str(run),checker,str(run/'capture_check.json')],stdout=(run/'capture_check.stdout').open('w')).returncode
    result=json.loads((run/'capture_check.json').read_text())
    assert (rc==0)==expected_pass, name
    assert result['component_capture_PASS']==expected_pass,name
    if cause:
        observed={int(x,16) for x in re.findall(r'causes=([0-9a-f]+)',(run/'diagnostic.log').read_text())}
        assert any(value & cause for value in observed), (name,cause,observed)
    source_rc=subprocess.run([sys.executable,'check_fullsix_source_schedule.py',str(run),'/srv/opentallas-scratch/claude/toksim-s81d-wqbp/runs/l0_p126/model',str(run/'source_schedule_check.json')],stdout=(run/'source_schedule.stdout').open('w')).returncode
    assert source_rc==0,name
    rows.append(dict(name=name,expected_capture_PASS=expected_pass,actual_capture_PASS=result['component_capture_PASS'],causal_fault_bit=hex(cause),cw_words=result['cw_words'],vp_words=result['vp_words'],missing_rows=len(result['missing']),matched_images=len(manifest),source_schedule_PASS=True))
    print('CAP_MATCHED_RECEIPT',json.dumps(rows[-1]))
Path('capture_qualification.json').write_text(json.dumps(dict(scope='CAP and VP capture component; not full-stage/consumer qualification',matched_nominal_and_negatives_PASS=True,full_stage_qualified=False,runs=rows),indent=2)+'\n')
