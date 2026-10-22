#!/usr/bin/env python3
"""Real-log admission negatives for source schedule checks; run on fleet."""
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

script=Path(__file__).with_name('check_fullsix_source_schedule.py')
if not script.exists():
    script=Path(__file__).resolve().parents[3]/'tools/s81_dv/layer_prog/check_fullsix_source_schedule.py'
spec=importlib.util.spec_from_file_location('schedule',script)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
run=Path('candidate')
model=Path('/srv/opentallas-scratch/claude/toksim-s81d-wqbp/runs/l0_p126/model')
raw=(run/'diagnostic.log').read_text()
assert module.check(run,model)['source_schedule_PASS']
mutants={
    'read_one_edge_late': raw.replace('ACTUAL_QREAD t=1557 ', 'ACTUAL_QREAD t=1558 ',1),
    'drop_live_half': raw.replace('gates=11 blocks=0,8','gates=01 blocks=0,8',1),
    'invalid_live_half': raw.replace('gates=01 blocks=32,40 parity=0 source=0,0 valid=10',
                                     'gates=01 blocks=32,40 parity=0 source=0,0 valid=00',1),
    'go_wrong_epoch': raw.replace('ACTUAL_GO t=1487 epoch=0','ACTUAL_GO t=1487 epoch=1',1),
    'extra_end': raw+'\nACTUAL_END t=11900 epoch=14 valid=00000\n',
    'payload_mismatch': raw+'\nRETAINED_QOUTPUT_MISMATCH half0 t=1558\n',
}
for name,log in mutants.items():
    assert log!=raw,name
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)
        (path/'diagnostic.log').write_text(log)
        result=module.check(path,model)
    assert not result['source_schedule_PASS'],name
    print('EXPECTED_CAUSAL_REJECTION',name,'missing',len(result['missing']),'extra',len(result['extra']))
print('SOURCE_SCHEDULE_REGRESSIONS PASS 1 nominal +6 causal negatives')
