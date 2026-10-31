"""gen_signed_parent_source.py (FLOW-19 10-31, COORD 15:4x, S81 ot_s81sl_capc5r): any released child sign-off policy at the
die period, child outline checked against its slot in the current parent (plan outline, no sibling overlap), opt-in
--enable-signed-physical drops the exit-78 guard.
    python3 -m pytest -q physical/die_plan/s81/cores/legacy/test_gen_signed_parent_source.py"""
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_signed_parent_source as S  # noqa: E402

VIEWS = HERE.parent / "views"
CAPTR = VIEWS / "captr_signed_1030" / "ot_s81sl_cap_tr"


def _copy(tmp_path, **policy):
    d = tmp_path / "ot_s81sl_cap_tr"
    shutil.copytree(CAPTR, d)
    so = json.loads((d / "signoff.json").read_text())
    so["policy"].update(policy)
    (d / "signoff.json").write_text(json.dumps(so))
    return d


def test_released_policy_other_than_60_25_is_accepted(tmp_path):
    # 12.24c nominal setup policy (uncertainty_setup 0, hold 25) is a released sign-off policy
    v = S.signed_view(_copy(tmp_path, uncertainty_setup_ps=0.0), 833)
    assert v["signoff"] == "SIGNED" and v["policy"]["uncertainty_setup_ps"] == 0.0
    assert v["outline_um"] == [90.72, 86.4]


def test_child_signed_at_another_period_is_refused(tmp_path):
    with pytest.raises(ValueError, match="period"):
        S.signed_view(_copy(tmp_path, period_ps=900.0), 833)


def _kids():
    return [dict(view="rt", inst="u_rt", at=[43.2, 43.2]), dict(view="tr", inst="u_tw", at=[43.2, 302.4]),
            dict(view="tr", inst="u_te", at=[216, 302.4])]


def test_slot_check_uses_the_current_parent_outline():
    views = {"rt": dict(outline_um=[259.2, 116.64]), "tr": dict(outline_um=[90.72, 86.4])}
    r = dict(S.slot_check(_kids(), views, [336.96, 414.72]))
    assert r["u_te"] == pytest.approx((216, 302.4, 306.72, 388.8))
    # a re-signed child may change its outline as long as it still fits its slot (was: must equal the old view)
    views["rt"] = dict(outline_um=[280.8, 120.96])
    S.slot_check(_kids(), views, [336.96, 414.72])


def test_slot_check_refuses_outside_and_overlap_and_rotates():
    views = {"rt": dict(outline_um=[300.0, 116.64]), "tr": dict(outline_um=[90.72, 86.4])}
    with pytest.raises(SystemExit, match="u_rt .* outside"):
        S.slot_check(_kids(), views, [336.96, 414.72])
    views = {"rt": dict(outline_um=[259.2, 270.0]), "tr": dict(outline_um=[90.72, 86.4])}
    with pytest.raises(SystemExit, match="overlaps u_rt"):
        S.slot_check(_kids(), views, [336.96, 414.72])
    k = [dict(view="tr", inst="u_r", at=[0, 0], orient="R90")]
    assert dict(S.slot_check(k, {"tr": dict(outline_um=[90.72, 86.4])}, [86.4, 90.72]))["u_r"] == (0, 0, 86.4, 90.72)
    with pytest.raises(SystemExit):
        S.slot_check(k, {"tr": dict(outline_um=[90.72, 86.4])}, [90.72, 86.4])


def test_capc5r_allowed_and_physical_opt_in():
    src = (HERE / "gen_signed_parent_source.py").read_text()
    assert "'ot_s81sl_capc5r'" in src and "--enable-signed-physical" in src
    assert "if not a.enable_signed_physical:" in src
