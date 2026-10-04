"""Caller plumbing only: fake callable is not a runtime or numerical verdict."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

P = Path(__file__).resolve().parents[1]/'tools/qwen_rom_combined_first_prepare.py'
spec = importlib.util.spec_from_file_location('first_prepare', P)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_first_prepare_consumes_existing_callable_not_legacy_pass_main(tmp_path, monkeypatch):
    source = tmp_path/'source'
    (source/'tools').mkdir(parents=True)
    for name in ['qwen_rom_combined_head_launch.py','qwen_rom_combined_head_readback.py']:
        (source/'tools'/name).write_text('# source protocol fixture\n')
    cache = tmp_path/'inputs.json'
    cache.write_text(json.dumps(dict(oracle=dict(root='cached-oracle',sha256='a'*64),
                                    baselines={'L3':{'status':'fail'}}, baseline_pending=['head'])))
    selection = tmp_path/'selection.json'
    output = tmp_path/'out'
    calls=[]
    def existing(book, inputs, out, root):
        assert book==selection and inputs==cache and root==source
        calls.append('prepare_from_inputs')
        out.mkdir()
        return ['actual-head-binary','--stages','stages.txt',str(out/'run')], {'status':'prepared'}
    api=SimpleNamespace(__file__=str(source/'tools/qwen_rom_combined_head_launch.py'),
                        prepare_from_inputs=existing,
                        main=lambda: (_ for _ in ()).throw(AssertionError('legacy PASS main forbidden')))
    monkeypatch.setattr(m.importlib,'import_module',lambda name:api)
    result=m.prepare(selection,cache,output,source)
    assert calls==['prepare_from_inputs'] and result['runtime_status']=='not_launched'
    assert not result['fulltoken_rtl_pass']
    assert result['checker_command'][result['checker_command'].index('--run-dir')+1]==str(output/'run')
    assert json.loads(cache.read_text())['baselines']['L3']['status']=='fail'


def test_wrong_source_root_refuses_before_calling_head_owner(tmp_path, monkeypatch):
    source=tmp_path/'source';source.mkdir()
    monkeypatch.setattr(m.importlib,'import_module',lambda name:SimpleNamespace(__file__='other/tools/head.py'))
    with pytest.raises(ValueError,match='different selected source root'):
        m.prepare('book','inputs',tmp_path/'out',source)
    assert not (tmp_path/'out').exists()


def test_initialized_head_selects_correct_owner_before_preparing(tmp_path, monkeypatch):
    source=tmp_path/'source';(source/'tools').mkdir(parents=True)
    names=[]
    def imported(name):
        names.append(name)
        def prepare(*args, **kwargs):
            raise ValueError('selected initialized owner reached')
        return SimpleNamespace(__file__=str(source/'tools'/(name+'.py')),prepare_from_inputs=prepare)
    monkeypatch.setattr(m.importlib,'import_module',imported)
    with pytest.raises(ValueError,match='selected initialized owner reached'):
        m.prepare('book','inputs',tmp_path/'out',source,initialized_head=True)
    assert names==['qwen_rom_combined_head_launch_initialized']
