"""DIE-KV-99 11-12: bind.load_asbuilt_netlist reads OUT/asbuilt.json or the gzipped OUT/asbuilt.json.gz (packaged cached
elaborations ship gzipped because GitHub rejects files > 100 MB)."""
import gzip
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bind  # noqa: E402

NET = {"creator": "test", "modules": {"m": {"ports": {}}}}


def test_plain(tmp_path):
    (tmp_path / "asbuilt.json").write_text(json.dumps(NET))
    assert bind.load_asbuilt_netlist(tmp_path) == NET


def test_gz(tmp_path):
    with gzip.open(tmp_path / "asbuilt.json.gz", "wt") as f:
        json.dump(NET, f)
    assert bind.load_asbuilt_netlist(tmp_path) == NET


def test_plain_wins_over_gz(tmp_path):
    (tmp_path / "asbuilt.json").write_text(json.dumps(NET))
    with gzip.open(tmp_path / "asbuilt.json.gz", "wt") as f:
        json.dump({"creator": "other", "modules": {}}, f)
    assert bind.load_asbuilt_netlist(tmp_path) == NET


def test_missing(tmp_path):
    with pytest.raises(bind.BindError):
        bind.load_asbuilt_netlist(tmp_path)
