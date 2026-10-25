import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("core_conns_directions", Path(__file__).with_name("core_conns_directions.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_shared_inputs_preserve_drivers_unknowns_and_bus_targets(tmp_path):
    for name, body in {"a": "PIN i[0]\n DIRECTION INPUT ;\nEND i[0]\nPIN o\n DIRECTION OUTPUT ;\nEND o", "b": "PIN i\n DIRECTION INPUT ;\nEND i"}.items():
        (tmp_path / (name + ".lef")).write_text(body)
    typ = {"hard_cores": [{"inst": c, "lef": c + ".lef"} for c in ("a", "b")]}
    con = {"a": {"i": ["core:b", "bus:ctl"], "o": ["core:b"], "unknown": ["core:b"]}, "b": {"i": ["core:a"]}}
    got = m.filter_shared_inputs(typ, con, tmp_path)
    # b.i has a genuine a.o driver, so retain the reverse relationship as well.
    assert got["a"]["i"] == ["bus:ctl"]
    assert got["a"]["o"] == ["core:b"]
    assert got["a"]["unknown"] == ["core:b"]
    assert got["b"]["i"] == ["core:a"]


def test_only_shared_inputs_drop_both_directions(tmp_path):
    (tmp_path / "x.lef").write_text("PIN i\n DIRECTION INPUT ;\nEND i")
    typ = {"hard_cores": [{"inst": c, "lef": "x.lef"} for c in ("a", "b")]}
    assert m.filter_shared_inputs(typ, {"a": {"i": ["core:b"]}, "b": {"i": ["core:a"]}}, tmp_path) == {}
