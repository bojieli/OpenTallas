import json
from pathlib import Path
import subprocess
import sys

import pytest
from extra_clock_roots import roots


def test_extra_roots_require_actual_output_and_no_second_driver(tmp_path):
    p = tmp_path/'die.v'
    p.write_text('module die();\nwire a;\nqfd_ckdiv6 div (.blk_o(a));\nendmodule\n')
    assert roots(p, {'qfd_ckdiv6': {'blk_o':'output'}}) == ['div/blk_o']
    with pytest.raises(ValueError): roots(p, {'qfd_ckdiv6': {'blk_o':'input'}})
    p.write_text(p.read_text().replace('endmodule', 'data other (.payload(a));\nendmodule'))
    with pytest.raises(ValueError, match='multiple'):
        roots(p, {'qfd_ckdiv6': {'blk_o':'output'}, 'data': {'payload':'output'}})


def test_legacy_extra_root_detection_is_empty(tmp_path):
    p = tmp_path/'die.v';p.write_text('module die();\nwire a;\nleaf u (.ck(a));\nendmodule\n')
    assert roots(p,{}) == []


def test_regional_numerical_pass_retains_model_only(tmp_path):
    fixtures = {
        'check':dict(neighbour_check=dict(classes={'intra:r0':dict(judged=True,over=0)},ff_measured=True)),
        'pairs':dict(summary=dict(pairs={}),lanes=[dict(bid='a',drift=0)]),
        'manifest':dict(physical_qualification_eligible=False,qualification=dict(scope='MODEL_ONLY'))}
    for name, data in fixtures.items(): (tmp_path/name).write_text(json.dumps(data))
    subprocess.run([sys.executable, str(Path(__file__).with_name('regional_verdict.py')),
                    *[str(tmp_path/n) for n in fixtures], '--out',str(tmp_path/'out')],check=True,capture_output=True)
    assert json.loads((tmp_path/'out').read_text())['verdict'] == 'MODEL_ONLY'


def test_opt_in_phy_has_complete_views_and_remains_model_only():
    import hashlib
    root = Path(__file__).resolve().parents[2]
    p = root/'physical/qwen_missing_phy/nface_tall_g5_lclk_1020/ot_qfd_ucie_x64_phy'
    d = json.loads((p/'ot_qfd_ucie_x64_phy.json').read_text())
    assert d['physical_qualification_eligible'] is False
    assert d['qualification'] == 'MODEL_ONLY'
    for name, sha in d['views'].items(): assert hashlib.sha256((p/name).read_bytes()).hexdigest() == sha
    assert 'output wire lclk' in (p/'ot_qfd_ucie_x64_phy_bb.v').read_text()
    assert 'USE CLOCK' in (p/'ot_qfd_ucie_x64_phy.lef').read_text().split('END lclk')[0]
