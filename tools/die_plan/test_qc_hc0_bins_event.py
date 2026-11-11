"""DIE-QC-97 11-10: the hc0 sink-bins plan event adds only clock.sink_bins_file (+ tap_pair_affinity {} when absent)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import qc_hc0_bins_event as E  # noqa: E402


def _plan():
    ck = lambda **k: dict(tap_mode="density", tap_max_sinks=1200, **k)
    return {"die": {"name": "q"}, "partition_types": {
        "a": {"clock": ck()}, "b": {"clock": ck(tap_pair_affinity={"max_group": 32})}, "c": {"clock": ck()}}}


def _bins(root, tn, typ=None, n=5):
    p = root / E.REL / f"{tn}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(bin_um=10.8, n=n, bins=[[5.4, 5.4, n]] if n else [], type=typ or tn)))


def test_adds_bins_and_default_pair_affinity_only(tmp_path):
    for t in "ab":
        _bins(tmp_path, t)
    P = _plan()
    Q, ch = E.apply(P, ["a", "b"], tmp_path)
    assert Q["partition_types"]["a"]["clock"]["sink_bins_file"] == f"{E.REL}/a.json"
    assert Q["partition_types"]["a"]["clock"]["tap_pair_affinity"] == {}
    assert Q["partition_types"]["b"]["clock"]["tap_pair_affinity"] == {"max_group": 32}   # existing spec kept
    assert Q["partition_types"]["c"] == P["partition_types"]["c"] and Q["die"] == P["die"]
    assert ch == {"a": ["clock.sink_bins_file", "clock.tap_pair_affinity = {}"], "b": ["clock.sink_bins_file"]}
    assert "sink_bins_file" not in P["partition_types"]["a"]["clock"]                      # input untouched


@pytest.mark.parametrize("case", ["missing_type", "no_file", "wrong_type", "empty", "already", "not_density"])
def test_refuses(tmp_path, case):
    P = _plan()
    _bins(tmp_path, "a", typ="b" if case == "wrong_type" else None, n=0 if case == "empty" else 5)
    if case == "no_file":
        (tmp_path / E.REL / "a.json").unlink()
    if case == "already":
        P["partition_types"]["a"]["clock"]["sink_bins_file"] = "x.json"
    if case == "not_density":
        P["partition_types"]["a"]["clock"]["tap_mode"] = "grid"
    with pytest.raises((ValueError, FileNotFoundError)):
        E.apply(P, ["zz"] if case == "missing_type" else ["a"], tmp_path)


def test_style_preserved():
    P = _plan()
    for kw in (dict(separators=(",", ":")), dict(separators=(", ", ": ")), dict(indent=1)):
        text = json.dumps(P, **kw) + "\n"
        assert E.dumps_like(P, text) == text
    with pytest.raises(ValueError):
        E.dumps_like(P, json.dumps(P, indent=3))


def test_listed_rows_are_the_unbinned_hc_rows():
    assert E.TYPES == ["sle_hc0__cl05696ed1", "sle_hc0__cl929603c0__cl38badc56", "sle_hc0__cl929603c0__cl4baa7c9c",
                       "slw_hc0__cl4f54b7a3"]
