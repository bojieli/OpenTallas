import json
from pathlib import Path
import shutil
import re
import pytest
from qwen_tp8.closed_specialization import verify
from qwen_tp8.bind_real import alias_view

ROOT=Path(__file__).resolve().parents[2]
MASTER='qfd_band_upper_tp8'
PROFILE='tools/qwen_tp8/profiles/qfd_band_upper_tp8.json'


@pytest.fixture
def repo(tmp_path):
    d=json.loads((ROOT/PROFILE).read_text())
    files={PROFILE,'rtl/qwen_split/qfd_band_upper_tp8.sv',
           'rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv',d['closed_recipe']}
    files.update(r['source'] for r in d['modules'].values())
    files.update(d['view']+'/'+name for name in d['view_sha256'])
    for f in files:
        p=tmp_path/f;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,p)
    return tmp_path,d


def test_exact_closed_source_and_view_alias(repo):
    root,d=repo;r=verify(root,MASTER)
    assert len(r['modules'])==14 and r['new_route_claim'] is False
    out=alias_view(root,root/'case',MASTER)
    source='ot_qfd_band_upper'
    for name in d['view_sha256']:
        if name=='abstract.json':continue
        target=out/name.replace(source,MASTER)
        if name.endswith('.lib'):
            normalize=lambda t,n:re.sub(r'cell\s*\(\s*"?'+n+r'"?\s*\)', 'cell(<identity>)', t)
            assert normalize(target.read_text(),MASTER)==normalize((root/d['view']/name).read_text(),source)
        elif name.endswith('.lef'):
            assert target.read_text().replace(MASTER,source)==(root/d['view']/name).read_text()
        else:assert target.read_bytes()==(root/d['view']/name).read_bytes()
    p=json.loads((out/'alias_provenance.json').read_text())
    assert p['source_specialization']['closed_record_sha256']==d['view_sha256']['abstract.json']


@pytest.mark.parametrize('change',['module','wrapper','lib','insertion','record'])
def test_changed_implementation_or_view_refused_before_alias_output(repo,change):
    root,d=repo
    if change=='module':
        f=d['modules']['ot_hdc_delay']['source'];p=root/f
        p.write_text(p.read_text().replace('module ot_hdc_delay','module ot_hdc_delay ',1))
    elif change=='wrapper':
        p=root/'rtl/qwen_split/qfd_band_upper_tp8.sv';p.write_text(p.read_text().replace('.RPIN(1)', '.RPIN(0)'))
    else:
        f={'lib':'ot_qfd_band_upper_tt.lib','insertion':'insertion.json','record':'abstract.json'}[change]
        p=root/d['view']/f;p.write_text(p.read_text()+'\n')
    with pytest.raises(ValueError):alias_view(root,root/'case',MASTER)
    assert not (root/'case/bound_views'/MASTER).exists()
