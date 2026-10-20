#!/usr/bin/env python3
"""Completed-looking captures cannot substitute for a matched terminal receipt."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

base=Path('/srv/opentallas-scratch/claude/toksim-s81d-wqbp')
raw=Path('candidate/diagnostic.log').read_text()
cases={
    'missing_terminal': ('\n'.join(line for line in raw.splitlines() if not line.startswith('FULLSIX_PREPARATORY_TRACE_END'))+'\n','1'),
    'unknown_source_failure': (raw.replace('FULLSIX_SOURCE_CHECK errors=3','FULLSIX_SOURCE_CHECK errors=4'),'1'),
    'wrong_simulator_status': (raw,'0'),
}
for name,(log,status) in cases.items():
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)
        (path/'diagnostic.log').write_text(log)
        (path/'simulator.exit').write_text(status+'\n')
        proc=subprocess.run([sys.executable,'check_fullsix_cap_capture.py',str(base/'root'),str(base/'root/sid6_fixture'),str(path),str(base/'wqbp_golden_check.py'),str(path/'check.json')],capture_output=True,text=True)
        result=json.loads((path/'check.json').read_text())
        assert proc.returncode!=0 and not result['component_capture_PASS'] and not result['terminal_receipt_PASS'],name
        assert result['cw_words']==512 and result['vp_words']==512,name
        print('EXPECTED_TERMINAL_REJECTION',name,'512 numerical captures retained')
print('CAP_TERMINAL_NEGATIVES PASS 3')
