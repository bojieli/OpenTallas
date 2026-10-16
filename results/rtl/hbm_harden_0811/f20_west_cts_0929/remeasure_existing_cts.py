import sys,json
from pathlib import Path
run=Path('/srv/opentallas-scratch/claude/ref_gate/hv16_vm_cal_f20_ww-20261016-090750')
sys.path.insert(0,str(run/'src/tools/ref_tile'))
from source_binding import run_staged_remeasurement
b=json.loads(Path(str(run)+'.source_snapshot.json').read_text())
print(json.dumps(run_staged_remeasurement(b,run,'/tmp/ref_gate_hv16_vm_cal_f20_ww_20261016-090750.sh'),indent=2))
