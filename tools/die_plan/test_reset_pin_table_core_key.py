"""KV-99 11-11: the module-keyed pin-table fallback in reset_tree.core_reset_targets must accept core pin tables that
name the module under "core" (schema opentallas.die_plan.core_pins.v1, e.g. qwen_kvsys/plan_of_record/pins/*.json), and
must still refuse two differing matching tables."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
PINS = [dict(name="rst_n", layer="M4", x=0, y=150)]


def _plan():
    raw = copy.deepcopy(TINY)
    raw.setdefault("reset", {}).update(release="wavefront")
    raw["partition_types"]["src"]["hard_cores"] = [dict(
        inst="u_c", module="m", origin_um=[50, 50], outline_um=[200, 300], pins_file="pins/m_pins.json")]
    return schema.Plan(raw)


def _tree(tmp_path, monkeypatch, tables):
    """Fake repo: tmp/tools/die_plan (HERE), tmp/physical/die_plan/<die>/pins/m_pins.json per table."""
    (tmp_path / "tools" / "die_plan").mkdir(parents=True)
    for i, tbl in enumerate(tables):
        d = tmp_path / "physical" / "die_plan" / f"die{i}" / "pins"
        d.mkdir(parents=True)
        (d / "m_pins.json").write_text(json.dumps(tbl))
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setattr(RT, "HERE", tmp_path / "tools" / "die_plan")


def test_core_keyed_pin_table_resolves(tmp_path, monkeypatch):
    _tree(tmp_path, monkeypatch, [dict(schema="opentallas.die_plan.core_pins.v1", core="m", pins=PINS)])
    out = RT.core_reset_targets(_plan(), "src")
    assert [o["inst"] for o in out] == ["u_c"]


def test_module_keyed_pin_table_still_resolves(tmp_path, monkeypatch):
    _tree(tmp_path, monkeypatch, [dict(module="m", pins=PINS)])
    assert [o["inst"] for o in RT.core_reset_targets(_plan(), "src")] == ["u_c"]


def test_other_core_table_is_not_picked(tmp_path, monkeypatch):
    _tree(tmp_path, monkeypatch, [dict(core="other", pins=PINS)])
    with pytest.raises(RT.ResetError, match="cannot uniquely resolve"):
        RT.core_reset_targets(_plan(), "src")


def test_two_differing_matching_tables_raise_ambiguity(tmp_path, monkeypatch):
    a = dict(core="m", pins=PINS)
    b = dict(core="m", pins=[dict(name="rst_n", layer="M4", x=0, y=140)])
    _tree(tmp_path, monkeypatch, [a, b])
    with pytest.raises(RT.ResetError, match="cannot uniquely resolve"):
        RT.core_reset_targets(_plan(), "src")


def test_two_identical_matching_tables_are_not_ambiguous(tmp_path, monkeypatch):
    t = dict(core="m", pins=PINS)
    _tree(tmp_path, monkeypatch, [t, t])
    assert [o["inst"] for o in RT.core_reset_targets(_plan(), "src")] == ["u_c"]
