import importlib.util
import json
from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]
BASE='results/uarch/dsrom_s73_pair1_20261003/baseline_s82_successor_r1'
PIN='717a32dcf35c09ccff432068691a3da40b610863'
API='3519c19f1'
spec=importlib.util.spec_from_file_location('c8_binding',ROOT/'tools/dsrom_c8_parent_binding.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@pytest.fixture
def owner(tmp_path,monkeypatch):
    run=subprocess.check_output
    names=[BASE+'/'+n for n in ('inventory.json','stage_map.json','physical_contract.json','return_baseline.json')]
    for name in names+['tools/dsrom_s82_payload_interface.py']:
        pin=API if name.startswith('tools/') else PIN
        data=run(['git','show',pin+':'+name],cwd=ROOT)
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    # Test owner files against exact repository objects without initializing a
    # duplicate repository or reading checkpoint payloads.
    monkeypatch.setattr(m.subprocess,'check_output',lambda args,**kw:run(args,**dict(kw,cwd=ROOT)))
    return tmp_path

def test_actual_s82_join_dynamic_phw_and_source_api(owner):
    p=m.ParentBinding(owner,BASE,PIN,API)
    x=p.field_parameters(41,3)
    assert x['die_id']==167 and x['field_pairs']==2388
    assert x['BF_pairs']==512 and x['physical_macros']==9552
    assert x['ROM_PHW']==10 and x['ROM_R']==128
    assert x['return_RD']==64 and x['return_ROOTD']==128
    assert x['WINDOW_REFILL_OWNER_SAFE']==1 and x['WINDOW_REFILL_CREDITS']==8
    assert p.scan_home(20)==41
    assert p.field_parameters(81,0)['ROM_PHW']==1
    assert p.payload_api_path==owner/'tools/dsrom_s82_payload_interface.py'
    with pytest.raises(ValueError):p.field_parameters(82,0)
    with pytest.raises(ValueError):p.field_parameters(41,True)

def test_reject_changed_owner_allocation_no_legacy_fallback(owner):
    f=owner/BASE/'stage_map.json';d=json.loads(f.read_text())
    d['PHW_required_by_stage'][41]=6;f.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='owner source changed'):
        m.ParentBinding(owner,BASE,PIN,API)

def test_parent_sources_require_actual_export_and_native_hooks(owner):
    p=m.ParentBinding(owner,BASE,PIN,API)
    with pytest.raises(FileNotFoundError):p.native_sources(owner/'absent')
    assert 'ot_v41_rt_die_l20_c8.sv' in m.SOURCES
    assert 'ot_dsrom_c8_write_journal.sv' in m.SOURCES
    assert 'ot_dsrom_c8_stage_context.sv' in m.SOURCES


def test_parent_export_refuses_source_substitution(owner):
    p=m.ParentBinding(owner,BASE,PIN,API)
    names=subprocess.check_output(['git','show',m.NATIVE_PIN+':tools/w17_current_fastpp_l20_window_owner_safe_sources.txt'],cwd=ROOT,text=True).split()
    export=owner/'native'
    for name in names:
        q=export/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text('unowned replacement')
    with pytest.raises(ValueError,match='native source changed'):
        p.native_sources(export)
