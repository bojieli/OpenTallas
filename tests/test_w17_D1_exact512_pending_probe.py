import json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'results/uarch/w17_D1_exact512_pending_probe_20261002'
def test_exact_parent_argv_not_other_program():
    p=json.loads((BASE/'plan.json').read_text())
    assert p['actual_argv']==[p['binary']['path']]
    assert p['program'] is None and p['no_relink_needed']
    assert p['expected_stop']==dict(cycles=512,time_ps=516000,evals=1545)
def test_probe_no_inferior_calls_writes_or_extra_run():
    s=(BASE/'capture.gdb').read_text()
    assert '\nset args\n' in s and '+DIR=' not in s
    assert '\nrun\n' not in s and '\ncall ' not in s
    assert 'set $root = (unsigned char*)$rdi' in s
    assert s.count('D1_OWNER_')==79
    assert s.count('break *')==1
