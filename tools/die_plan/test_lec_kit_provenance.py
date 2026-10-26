"""Standalone kits bind their copied tool and inputs to the generator checkout."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def test_standalone_receipt_accepts_exact_inputs_and_rejects_mutants(tmp_path, monkeypatch):
    kit = tmp_path / 'kit'
    (kit / 'rtl').mkdir(parents=True)
    (kit / 'rtl' / 'tiny.sv').write_text('module tiny(input d, output q); assign q=d; endmodule\n')
    (kit / 'config.mk').write_text('export DESIGN_NAME = tiny\n')
    (kit / 'lec.py').write_bytes(Path(lec.__file__).read_bytes())
    source = {'commit': 'ab' * 20, 'dirty': False, 'source': 'git'}
    (kit / 'freeze.json').write_text(json.dumps({'source_commit': source['commit'], 'kit_hash': '0123'}))
    lec.write_kit_provenance(kit, tmp_path, provenance=source)
    monkeypatch.setattr(lec, '_repo_provenance', lambda repo=None: {'commit': None, 'dirty': None})
    assert lec._provenance(kit)['commit'] == source['commit']
    receipt = (kit / 'PROVENANCE.json').read_text()
    for key, value in [('commit', 'cd' * 20), ('commit', 'not-a-sha'), ('dirty', True)]:
        bad = json.loads(receipt)
        bad['provenance'][key] = value
        (kit / 'PROVENANCE.json').write_text(json.dumps(bad))
        assert lec._provenance(kit)['commit'] is None
    (kit / 'PROVENANCE.json').write_text(receipt)
    for rel in ['config.mk', 'rtl/tiny.sv', 'lec.py', 'freeze.json']:
        p = kit / rel
        original = p.read_bytes()
        p.write_bytes(original + b'\n// changed\n')
        assert lec._provenance(kit)['commit'] is None
        p.write_bytes(original)
    # Newly introduced source files also invalidate the staged inventory.
    (kit / 'rtl' / 'extra.sv').write_text('module extra; endmodule\n')
    assert lec._provenance(kit)['commit'] is None
    (kit / 'rtl' / 'extra.sv').unlink()
    assert lec._provenance(kit)['commit'] == source['commit']
    other_tool = tmp_path / 'other_lec.py'
    other_tool.write_text('# different running tool\n')
    with monkeypatch.context() as m:
        m.setattr(lec, '__file__', str(other_tool))
        assert lec._provenance(kit)['commit'] is None


def test_repository_provider_remains_authoritative(tmp_path, monkeypatch):
    source = {'commit': 'cd' * 20, 'dirty': True, 'source': 'git'}
    monkeypatch.setattr(lec, '_repo_provenance', lambda repo=None: source)
    assert lec._provenance(tmp_path) == source  # no new waiver or clean claim
