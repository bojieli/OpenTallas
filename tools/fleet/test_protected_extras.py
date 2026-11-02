from pathlib import Path
import importlib.util
import pytest

spec = importlib.util.spec_from_file_location('protected_extras', Path(__file__).with_name('protected_extras.py'))
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


def test_explicit_retirements_preserve_every_other_row(tmp_path):
    cache, retired = tmp_path/'extra.tsv', tmp_path/'retired.tsv'
    keep = '# keep comment\nintel2\t/old/b_fx\tother host\nintel1\t/old/b_fx/child\tchild evidence\nintel1\t/current\tcurrent missing still protected\n'
    cache.write_text('intel1\t/old/b_fx\tretired build\n' + keep)
    retired.write_text('intel1\t/old/b_fx\ta04cee8bc\towner retired superseded build\n')
    assert P.reconcile(cache, retired, write=True) == keep
    assert cache.read_text() == keep


def test_stale_historical_addition_cannot_resurrect_retirement(tmp_path):
    cache, retired, added = [tmp_path/n for n in ['extra.tsv','retired.tsv','old_origin.tsv']]
    cache.write_text('intel1\t/current\tcurrent\n')
    retired.write_text('intel1\t/old/b_fx\ta04cee8bc\towner retired\n')
    added.write_text('intel1\t/old/b_fx\tstale old description\nintel1\t/new\tnew owner request\n')
    assert P.reconcile(cache, retired, added, True) == 'intel1\t/current\tcurrent\nintel1\t/new\tnew owner request\n'
    before = cache.read_text()
    with pytest.raises(FileNotFoundError):
        P.reconcile(cache, tmp_path/'missing_receipt', write=True)
    assert cache.read_text() == before


def test_owned_hook_copy_changes_only_manual_cache_sites(tmp_path):
    src, out = tmp_path/'paused', tmp_path/'own'
    src.mkdir()
    cycle = 'count_signed\ncat newlane$N.tsv >> extra_protect.tsv; echo rows\nbash regen_protect.sh >> sum\nbash audit.sh\n'
    regen = 'generate_signed_and_nearcount\n{ echo extras; cat extra_protect.tsv; } >> PROTECTED-DBS.txt\nmissing_audit_unchanged\n'
    (src/'cycle.sh').write_text(cycle); (src/'regen_protect.sh').write_text(regen)
    P.hooks(src, out, tmp_path/'retired.tsv')
    assert (src/'cycle.sh').read_text() == cycle
    assert (src/'regen_protect.sh').read_text() == regen
    assert 'count_signed\n' in (out/'cycle.sh').read_text()
    assert 'bash audit.sh\n' in (out/'cycle.sh').read_text()
    assert 'generate_signed_and_nearcount\n' in (out/'regen_protect.sh').read_text()
    assert 'missing_audit_unchanged\n' in (out/'regen_protect.sh').read_text()
    assert '--retired' in (out/'regen_protect.sh').read_text()
