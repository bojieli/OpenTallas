#!/usr/bin/env python3
"""Source-derived CAP lowering must reject incompatible source contracts."""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

root=Path('/srv/opentallas-scratch/claude/toksim-s81d-wqbp/root')
model=Path('/srv/opentallas-scratch/claude/toksim-s81d-wqbp/runs/l0_p126/model')
contract=json.loads((model/'contract.json').read_text())
source=(model/'source_ctl.txt').read_text()
cases=[]
bad=copy.deepcopy(contract);bad['global_calendar']['shifts']['R01']=0
cases.append(('wrong_CAP_LD_contract',bad,source,'AssertionError'))
bad=copy.deepcopy(contract);bad['actual_frames']=5
cases.append(('partial_frame_set',bad,source,'AssertionError'))
bad=copy.deepcopy(contract)
cases.append(('XR_CTL_collision',bad,source+'1816 00000000000000000000000000000000000000000000000\n','XR_CTL_COLLISION'))
for name,data,ctl,witness in cases:
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)
        (path/'contract.json').write_text(json.dumps(data))
        (path/'source_ctl.txt').write_text(ctl)
        proc=subprocess.run([sys.executable,'compile_fullsix_cap_program.py',str(root),str(path),str(path/'output')],capture_output=True,text=True)
        assert proc.returncode!=0 and witness in proc.stderr,(name,proc.stdout,proc.stderr)
        print('EXPECTED_COMPILER_REJECTION',name,witness)
print('CAP_COMPILE_NEGATIVES PASS 3')
