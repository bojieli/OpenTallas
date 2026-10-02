import json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_D1_materialized_prerequisite_guard as guard

def test_complete_source_only_prerequisites():
    r=guard.validate();assert r['files']==136 and not r['private_ROOT_reads'] and r['compiler_invocations']==r['simulations']==0

@pytest.mark.parametrize('bad',['missing','drift','escape'])
def test_prerequisite_fail_closed_before_any_compiler(tmp_path,bad):
    rec=tmp_path/'results/uarch/w17_D1_portable_successor_20261002';rec.mkdir(parents=True)
    p=tmp_path/'dependency';p.write_bytes(b'correct')
    import hashlib
    m=dict(source_pin='4e38326d6f361bc85e660f48c59c355e2bb95274',files={'dependency':dict(bytes=7,sha256=hashlib.sha256(b'correct').hexdigest())},total_bytes=7)
    if bad=='missing':p.unlink()
    elif bad=='drift':p.write_bytes(b'changed')
    else:m['files']['../escape']=m['files'].pop('dependency')
    (rec/'prerequisite_manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError):guard.validate(tmp_path)

def test_unenrolled_source_queries_never_run_git():
    import w17_D1_portable_pytest as adapter
    with pytest.raises(ValueError):adapter.exact_source(['git','show','other-private-branch:secret'])
    with pytest.raises(ValueError):adapter.exact_source(['cat','/tmp/private'])


def test_committed_git_authority_contains_three_real_admission_sources():
    m=json.loads((guard.REC/'prerequisite_manifest.json').read_text())
    for name in ['rtl/test/v41_runtime/ot_v41_rt_die.sv','rtl/hdc/v41x/ot_hdc_core_v41x.sv','rtl/chip/ot_chip_v41x_die.sv']:
        assert m['source_pin']+':'+name in m['test_git_authority']
