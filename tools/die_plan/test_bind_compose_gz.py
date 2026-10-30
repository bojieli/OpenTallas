"""bind_compose.apply reads a gzip-committed composition spec (x.json.gz, or x.json absent beside x.json.gz)."""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_compose as bc  # noqa: E402


class _B:
    def __init__(self, base):
        self.base, self.F, self.R, self.extra_lib = str(base), None, None, []


def test_gz_and_plain(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(bc, "compose", lambda F, R, spec, Cell: (seen.append(spec) or ([], {"ok": 1})))
    monkeypatch.setitem(sys.modules, "bind_elab", type(sys)("bind_elab"))
    sys.modules["bind_elab"].Cell = None
    spec = {"a": [1, 2]}
    (tmp_path / "c.json.gz").write_bytes(gzip.compress(json.dumps(spec).encode()))
    for name in ("c.json", "c.json.gz"):
        bc.apply(_B(tmp_path), name)
        assert seen[-1] == spec
        assert (tmp_path / "composed_rtl" / "receipt.json").exists()
    (tmp_path / "p.json").write_text(json.dumps({"p": 1}))
    bc.apply(_B(tmp_path), "p.json")
    assert seen[-1] == {"p": 1}
