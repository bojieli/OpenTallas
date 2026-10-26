"""Original ROM identity survives shared wrappers; selectors never replace payloads."""
from types import SimpleNamespace
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind


RULE = [{"module": "rom", "param": "INSTANCE"}]


def cell(path, value='""'):
    return SimpleNamespace(path=path, module="rom", ytype="rom", params={"INSTANCE": value})


def test_distinct_original_instances_and_explicit_image():
    a, b, c = cell("u_a.u_rom"), cell("u_b.u_rom"), cell("u_c.u_rom", '"u_c.u_rom"')
    audit = bind.instance_path_params([a, b, c], {}, RULE)
    assert [x["inst"] for x in audit] == ["u_a.u_rom", "u_b.u_rom"]
    assert a.params["INSTANCE"] == '"u_a.u_rom"'
    assert b.params["INSTANCE"] == '"u_b.u_rom"'
    assert c.params["INSTANCE"] == '"u_c.u_rom"'
    # The existing shared-type value collector must expose differing selectors.
    B = object.__new__(bind.Binder)
    B.tsig, B.tvals, B.tparams = {}, {}, {}
    sigs = {"a": ({"same": True}, {("param", "u_rom", "INSTANCE"): a.params["INSTANCE"]}),
            "b": ({"same": True}, {("param", "u_rom", "INSTANCE"): b.params["INSTANCE"]})}
    B._type_vals("tile", ["a", "b"], sigs)
    assert B.tparams["tile"][("param", "u_rom", "INSTANCE")] == ['"u_a.u_rom"', '"u_b.u_rom"']


def test_default_and_disabled():
    c = cell("u_a.u_rom")
    c.params = {}
    assert bind.instance_path_params([c], {}, []) == []
    assert c.params == {}
    bind.instance_path_params([c], {("rom", "rom"): {"INSTANCE": '""'}}, RULE)
    assert c.params == {"INSTANCE": '"u_a.u_rom"'}


@pytest.mark.parametrize("bad", ["../rom", 'u_"rom', "u\\rom", ""])
def test_bad_image_identity(bad):
    with pytest.raises(bind.BindError, match="unsafe"):
        bind.instance_path_params([cell(bad)], {}, RULE)


def test_missing_nonstrings_duplicate_and_unmatched_rejected():
    c = cell("u_rom", "12")
    with pytest.raises(bind.BindError, match="declared string"):
        bind.instance_path_params([c], {}, RULE)
    with pytest.raises(bind.BindError, match="duplicate"):
        bind.instance_path_params([cell("u_rom")], {}, RULE + RULE)
    with pytest.raises(bind.BindError, match="no elaborated"):
        bind.instance_path_params([], {}, RULE)
    with pytest.raises(bind.BindError, match="differs from original"):
        bind.instance_path_params([cell("u_a.u_rom", '"u_b.u_rom"')], {}, RULE)
