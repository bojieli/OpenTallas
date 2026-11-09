"""DIE-S81-85 11-09: the LEC proof policy is recorded in the kit (lec_options.json) by gen_core_kit_legacy.py and read by
legacy_gate.py lec (and lec_async.sh); the launching shell no longer decides it.
    python3 -m pytest -q physical/die_plan/s81/cores/legacy/test_lec_options_kit.py"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[4] / "tools/die_plan"))
import gen_core_kit_legacy as G  # noqa: E402
import legacy_gate as gate  # noqa: E402


def test_recipe_opt_in_writes_and_regeneration_drops(tmp_path):
    G.write_lec_options(tmp_path, {"lec": {"superset_vec": True}}, "m", True)
    assert json.loads((tmp_path / "lec_options.json").read_text()) == {"superset_vec": True}
    G.write_lec_options(tmp_path, {}, "m", True)
    assert not (tmp_path / "lec_options.json").exists()


@pytest.mark.parametrize("rec,modern", [({"lec": {"superset_vec": 1}}, True), ({"lec": {"other": True}}, True),
                                        ({"lec": {"superset_vec": True}}, False)])
def test_recipe_bad_or_legacy_refused(tmp_path, rec, modern):
    with pytest.raises(SystemExit):
        G.write_lec_options(tmp_path, rec, "m", modern)


def test_bksel_p_recipe_carries_superset():
    rec = json.loads((HERE / "profiles/bksplit_1108/recipes.json").read_text())["ot_s81ph_hq_pk2"]
    assert rec["lec"] == {"superset_vec": True}


def test_gate_lec_env_reads_kit_policy(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_LEC_SUPERSET_VEC", raising=False)
    (tmp_path / "config.mk").write_text("")
    assert "OT_LEC_SUPERSET_VEC" not in gate.lec_env(tmp_path)
    (tmp_path / "lec_options.json").write_text('{"superset_vec": true}\n')
    assert gate.lec_env(tmp_path)["OT_LEC_SUPERSET_VEC"] == "1"
    monkeypatch.setenv("OT_LEC_SUPERSET_VEC", "1")
    assert gate.lec_env(tmp_path)["OT_LEC_SUPERSET_VEC"] == "1"
    monkeypatch.setenv("OT_LEC_SUPERSET_VEC", "0")
    with pytest.raises(ValueError):
        gate.lec_env(tmp_path)
    (tmp_path / "lec_options.json").write_text('{"superset_vec": "yes"}\n')
    monkeypatch.delenv("OT_LEC_SUPERSET_VEC")
    with pytest.raises(ValueError):
        gate.lec_env(tmp_path)
