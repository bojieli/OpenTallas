import pytest
import qc_su_vmw_land_event as E


def lanes(l0=18, l1=19, drop=None):
    out = {}
    for s in [f"{d}{i}" for d in "EW" for i in range(6)]:
        out[f"sl_{s}_su_l0__x_su_l0_ctl"] = {"cycles": l0}
        out[f"sl_{s}_su_l1__x_su_l1_ctl"] = {"cycles": l1}
    if drop:
        del out[drop]
    return out


def test_one_group_per_slice():
    g = E.groups(lanes())
    assert len(g) == 12 and {x["kind"] for x in g} == {"bus"}
    assert g[0]["lanes"] == ["sl_E0_su_l0__x_su_l0_ctl", "sl_E0_su_l1__x_su_l1_ctl"]


def test_equal_depth_is_accepted():
    assert len(E.groups(lanes(19, 19))) == 12


def test_refuses_su_l0_slower():
    with pytest.raises(SystemExit):
        E.groups(lanes(20, 19))


def test_refuses_missing_slice():
    with pytest.raises(SystemExit):
        E.groups(lanes(drop="sl_W5_su_l0__x_su_l0_ctl"))


def test_refuses_missing_partner():
    with pytest.raises(SystemExit):
        E.groups(lanes(drop="sl_W5_su_l1__x_su_l1_ctl"))
