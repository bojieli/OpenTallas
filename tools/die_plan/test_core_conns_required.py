import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import check


def test_explicit_core_connections_are_loaded(tmp_path):
    expected = {"tile": {"u_core": {"data": ["bus:out"]}}}
    path = tmp_path / "connections.json"
    path.write_text(json.dumps(expected))
    assert check.load_core_conns(path=path) == expected


def test_explicit_missing_core_connections_fail_closed(tmp_path):
    with pytest.raises(FileNotFoundError, match="explicit --core-conns"):
        check.load_core_conns(path=tmp_path / "misspelled-sidecar.json")
    # Legacy optional discovery is still optional when no path was requested.
    assert check.load_core_conns(plan_dir=tmp_path) == {}
