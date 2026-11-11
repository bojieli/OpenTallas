"""DIE-QC-97 11-10: the PLAN-GEN-RULES-1 rule-B bins event adds only clock.sink_bins_file (+ tap_pair_affinity {} when
absent) on density rows; rows that already have bins / a tap_group, or no density clock, are kept and reported."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import qc_pgr_bins_event as E  # noqa: E402


def _plan():
    ck = lambda **k: dict(tap_mode="density", tap_max_sinks=1200, **k)
    return {"die": {"name": "q"}, "partition_types": {
        "a": {"clock": ck()}, "b": {"clock": ck(tap_pair_affinity={"max_group": 32})}, "c": {"clock": ck()},
        "d": {"clock": ck(sink_bins_file="old/d.json")}, "e": {"clock": ck(tap_group="g1")},
        "f": {"clock": {"tap_mode": "explicit"}}, "g": {"clock": {"tap_pitch_um": 300}}}}


def _bins(root, tn, typ=None, n=5):
    p = root / E.REL / f"{tn}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(bin_um=10.8, n=n, bins=[[5.4, 5.4, n]] if n else [], type=typ or tn)))


def test_adds_bins_and_default_pair_affinity_only(tmp_path):
    for t in "ab":
        _bins(tmp_path, t)
    P = _plan()
    Q, ch, kept = E.apply(P, ["a", "b", "d", "e", "f", "g"], tmp_path)
    assert Q["partition_types"]["a"]["clock"]["sink_bins_file"] == f"{E.REL}/a.json"
    assert Q["partition_types"]["a"]["clock"]["tap_pair_affinity"] == {}
    assert Q["partition_types"]["b"]["clock"]["tap_pair_affinity"] == {"max_group": 32}   # existing spec kept
    for t in "cdefg":
        assert Q["partition_types"][t] == P["partition_types"][t]
    assert Q["die"] == P["die"]
    assert ch == {"a": ["clock.sink_bins_file", "clock.tap_pair_affinity = {}"], "b": ["clock.sink_bins_file"]}
    assert sorted(kept) == ["d", "e", "f", "g"] and "old/d.json" in kept["d"] and "g1" in kept["e"]
    assert "sink_bins_file" not in P["partition_types"]["a"]["clock"]                      # input untouched


@pytest.mark.parametrize("case", ["missing_type", "no_file", "wrong_type", "empty"])
def test_refuses(tmp_path, case):
    P = _plan()
    _bins(tmp_path, "a", typ="b" if case == "wrong_type" else None, n=0 if case == "empty" else 5)
    if case == "no_file":
        (tmp_path / E.REL / "a.json").unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        E.apply(P, ["zz"] if case == "missing_type" else ["a"], tmp_path)


def test_style_preserved():
    P = _plan()
    for kw in (dict(separators=(",", ":")), dict(separators=(", ", ": ")), dict(indent=1)):
        text = json.dumps(P, **kw) + "\n"
        assert E.dumps_like(P, text) == text
    assert E.dumps_like(P, json.dumps(P, indent=1)) == json.dumps(P, indent=1)
    with pytest.raises(ValueError):
        E.dumps_like(P, json.dumps(P, indent=3))


def test_listed_rows_have_bins_files():
    root = Path(__file__).resolve().parents[2]
    assert len(E.TYPES) == 14 and len(set(E.TYPES)) == 14
    for tn in E.TYPES:
        d = json.loads((root / E.REL / f"{tn}.json").read_text())
        assert d["type"] == tn and d["n"] == sum(b[2] for b in d["bins"]) > 0
