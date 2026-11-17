"""HEAD-DIE-R 11-16: check.py finds the native reset receipt bound to the plan digest without a CLI flag."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check as C
import head_native_release as HNR


class _P:
    def __init__(self, raw):
        self.raw = raw


def _receipt(root, name, plan_sha, schema='opentallas.head_native_release.v1'):
    d = root / 'results' / name
    d.mkdir(parents=True)
    f = d / 'native_release_receipt.json'
    f.write_text(json.dumps(dict(schema=schema, plan_sha256=plan_sha)))
    return f


def test_matching_digest_is_found(tmp_path):
    P = _P({'die': {'name': 'x'}, 'a': 1})
    _receipt(tmp_path, 'old', 'f' * 64)
    want = _receipt(tmp_path, 'new', HNR.digest(P.raw))
    assert C.find_native_reset_receipt(P, tmp_path) == str(want)


def test_no_match_keeps_pending_default(tmp_path):
    P = _P({'die': {'name': 'x'}, 'a': 2})
    _receipt(tmp_path, 'other', HNR.digest({'a': 3}))
    _receipt(tmp_path, 'wrongschema', HNR.digest(P.raw), schema='something.else')
    (tmp_path / 'results' / 'broken').mkdir()
    (tmp_path / 'results' / 'broken' / 'native_release_receipt.json').write_text('{not json')
    assert C.find_native_reset_receipt(P, tmp_path) is None


def test_missing_results_dir(tmp_path):
    assert C.find_native_reset_receipt(_P({'a': 1}), tmp_path) is None
