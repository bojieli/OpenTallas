"""Regression for extraction falling back to missing default glue instead of the built case."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib.util

import pytest


spec = importlib.util.spec_from_file_location('extract_die', Path(__file__).with_name('extract_die.py'))
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)


def lint_for_case():
    lint = SimpleNamespace(R8_ACTIVE=[False], GLUE_CASE=[None])
    lint.S = SimpleNamespace(glue_rtl=lambda model: f"module {model['master']}(input [{model['width']-1}:0] in); endmodule\n")

    def real_blocks(die, model):
        # The old extractor never set GLUE_CASE, so it read an absent default file.
        text = Path(lint.GLUE_CASE[0] or '/missing/default/dsfd_glue.sv').read_text()
        assert f"module {model['master']}" in text
        assert f"[{model['width']-1}:0]" in text
        return {model['master']: {'direction': 'input'}}

    lint.real_blocks = real_blocks
    return lint


def test_uses_current_case_instead_of_default_glue(tmp_path):
    lint = lint_for_case()
    model = dict(master='recipe_specific_relay', width=538)
    real, provenance = extract.case_real_blocks(lint, 's81r8_layer1', model, tmp_path/'clock'/'model.json.gz')
    assert list(real) == ['recipe_specific_relay']
    assert lint.R8_ACTIVE == [True]
    path = Path(provenance['path'])
    assert path.name == 'model_glue.sv'
    assert provenance['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_supplied_generated_glue_is_preserved_and_bound(tmp_path):
    lint = lint_for_case()
    model = dict(master='case_relay', width=17)
    glue = tmp_path/'generated.sv'
    original = lint.S.glue_rtl(model) + '// actual case identity\n'
    glue.write_text(original)
    _, provenance = extract.case_real_blocks(lint, 's81r8_layer1', model, tmp_path/'model.json.gz', glue)
    assert glue.read_text() == original
    assert provenance['kind'] == 'supplied case glue'
    assert provenance['sha256'] == hashlib.sha256(original.encode()).hexdigest()


def test_missing_supplied_glue_fails_instead_of_empty_real_blocks(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract.case_real_blocks(lint_for_case(), 's81r8_layer1', {}, tmp_path/'model.json.gz', tmp_path/'missing.sv')
    assert not (tmp_path/'model.json.gz').exists()


def test_real_source_failure_propagates(tmp_path):
    lint = lint_for_case()
    def missing_source(die, model):
        raise FileNotFoundError('missing_native_source.sv')
    lint.real_blocks = missing_source
    with pytest.raises(FileNotFoundError, match='missing_native_source'):
        extract.case_real_blocks(lint, 's81r8_layer1', dict(master='test', width=1), tmp_path/'model.json.gz')


def test_other_die_does_not_accept_s81_glue(tmp_path):
    with pytest.raises(ValueError, match='only supported'):
        extract.case_real_blocks(lint_for_case(), 'hbm', {}, tmp_path/'model.json.gz', tmp_path/'file.sv')
