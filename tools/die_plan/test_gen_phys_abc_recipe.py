"""KIT-SYNTH-TARGET-1119: the kit-owned ABC recipe is selectable per die (budgets.abc_recipe), per type (abc_recipe_types) or per
row (OT_ABC_RECIPE); `stock` leaves the ORFS abc_speed.script alone; the delay target replaces @D@."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def test_default_is_kit_and_overrides(monkeypatch):
    monkeypatch.delenv("OT_ABC_RECIPE", raising=False)
    assert gen_phys._abc_recipe({}, "svc_hi__t2") == "kit"
    assert gen_phys._abc_recipe({"abc_recipe": "stock"}, "x") == "stock"
    b = {"abc_recipe": "stock", "abc_recipe_types": {"svc_hi": "kit"}}
    assert gen_phys._abc_recipe(b, "svc_hi__t2") == "kit"
    monkeypatch.setenv("OT_ABC_RECIPE", "stock")
    assert gen_phys._abc_recipe(b, "svc_hi__t2") == "stock"
    monkeypatch.setenv("OT_ABC_RECIPE", "bogus")
    with pytest.raises(ValueError):
        gen_phys._abc_recipe({}, "x")


def test_install_substitutes_target(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_ABC_RECIPE", raising=False)
    monkeypatch.delenv("OT_ABC_TARGET_PS", raising=False)
    assert gen_phys._abc_install({"abc_target_ps": 550}, "t", tmp_path, REPO) == "kit"
    text = (tmp_path / "abc_kit.script").read_text()
    assert "&nf -D 550" in text and "@D@" not in text and "#" not in text and "&if -g -K 6" in text
    assert gen_phys._abc_install({"abc_recipe": "stock"}, "t", tmp_path / "x", REPO) is None
