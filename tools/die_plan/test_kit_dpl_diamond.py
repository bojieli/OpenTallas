"""DIE-QC-65/KITS 11-03: gen phys --dpl-diamond TYPES puts only the named types' kits on the diamond detailed-placement
legalizer (DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer); other kits are unchanged; the plan budget form
(budgets.dpl_legalizer, FLOW-7) still gives the same line.
    python3 -m pytest -q tools/die_plan/test_kit_dpl_diamond.py"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen  # noqa: E402
import gen_phys  # noqa: E402
import schema  # noqa: E402

TINY = HERE / "examples" / "tiny_plan.json"
LINE = "export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer"


def _P():
    return schema.Plan(json.loads(TINY.read_text()))


def test_default_kit_has_no_dpl_args():
    with tempfile.TemporaryDirectory() as d:
        cfg = (gen_phys.write_type_kit(_P(), "mid", d, []) / "config.mk").read_text()
        assert "DETAIL_PLACEMENT_ARGS" not in cfg


def test_dpl_diamond_kit():
    with tempfile.TemporaryDirectory() as d:
        cfg = (gen_phys.write_type_kit(_P(), "mid", d, [], dpl_diamond=True) / "config.mk").read_text()
        assert cfg.count(LINE) == 1


def test_budget_form_unchanged():
    assert gen_phys._dpl_args({}) == [] and gen_phys._dpl_args({}, diamond=True) == [LINE]
    assert gen_phys._dpl_args({"dpl_legalizer": "diamond"}) == [LINE]
    assert gen_phys._dpl_args({"dpl_legalizer": "diamond"}, diamond=True) == [LINE]


def test_gen_phys_cli_dpl_diamond_only_named_types():
    with tempfile.TemporaryDirectory() as d:
        assert gen.main(["phys", str(TINY), "--out", d, "--types", "mid,sink", "--dpl-diamond", "mid", "--trial"]) == 0
        cfgs = {p.parent.name: p.read_text() for p in Path(d).rglob("config.mk")}
        mid = [v for k, v in cfgs.items() if "mid" in k]
        sink = [v for k, v in cfgs.items() if "sink" in k]
        assert mid and sink, sorted(cfgs)
        assert all(LINE in v for v in mid) and not any("DETAIL_PLACEMENT_ARGS" in v for v in sink)
