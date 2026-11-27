"""CA-FREG-1: head_current_ca.apply_freg carries sidecar freg flags into a fresh CA plan (default-off flag --freg-from)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_current_ca as H  # noqa: E402


def test_apply_freg_adds_one_cycle_once_and_ignores_unknown():
    doc = {"crossings": [{"port": "a", "lat_cycles": 3}, {"port": "b", "lat_cycles": 3}, {"port": "c", "lat_cycles": 2, "freg": 1}]}
    ports = {"a": {"freg": 1}, "b": {"freg": 0}, "c": {"freg": 1}, "zz": {"freg": 1}}
    new, n = H.apply_freg(doc, ports)
    assert n == 1
    by = {r["port"]: r for r in new["crossings"]}
    assert (by["a"]["freg"], by["a"]["lat_cycles"]) == (1, 4)
    assert "freg" not in by["b"] and by["b"]["lat_cycles"] == 3
    assert by["c"]["lat_cycles"] == 2                     # already declared: not added twice
    assert doc["crossings"][0]["lat_cycles"] == 3         # input untouched
    assert H.apply_freg(new, ports)[1] == 0               # idempotent


def test_flag_is_default_off():
    src = (Path(__file__).resolve().parent / "head_current_ca.py").read_text()
    assert "'--freg-from', type=Path, default=None" in src


def test_apply_freg_bumps_edge_latency_when_present():
    new, n = H.apply_freg({"crossings": [{"port": "a", "lat_cycles": 3, "lat_cycles_edge": 4}]}, {"a": {"freg": 1}})
    assert n == 1 and new["crossings"][0]["lat_cycles_edge"] == 5 and new["crossings"][0]["lat_cycles"] == 4
