"""DIE-HBM-90-TSTRAP 11-07: fit die.pg.domains rects to their SerDes partition (HBM d44v NW_io shape).

NW_io (0,6065.28) 648 x 4320 holds the PHY u_lk_N0 at (34.56,34.56) 600.048 x 600.48 and the endpoint core u_ep_N0
at (112.32,1088.64); its window/bump field is (0,6065.28)-(634.608,7115.28), the domain that field + 63.64 um.  The
halo covers 63.64 um of NW_su21 (q_su21, no macro) and cuts u_ep_N0, so gen_phys.phy_pg_domains stops both types.
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fit_phy_pg_domains as F  # noqa: E402
import gen_phys as GP  # noqa: E402


class FakePlan:
    def __init__(self, domain, ep_y=1088.64):
        self.types = {
            "NW_io": dict(outline_um=[648.0, 4320.0], contents=[
                dict(inst="u_lk_N0", module="ot_pdie_serdes", origin_um=[34.56, 34.56], outline_um=[600.048, 600.48]),
                dict(inst="u_ep_N0", module="hfd_ep_static", origin_um=[112.32, ep_y], outline_um=[427.68, 246.24])]),
            "q_su21": dict(outline_um=[1892.16, 1555.2], contents=[
                dict(inst="u_x", module="x", origin_um=[800.0, 100.0], outline_um=[100.0, 100.0])])}
        self.parts = {"NW_io": dict(type="NW_io", origin_um=[0.0, 6065.28], orient="R0"),
                      "NW_su21": dict(type="q_su21", origin_um=[0.0, 4510.08], orient="R0")}
        self.die = dict(io=[dict(name="io_NW_io_u_lk_N0", part="NW_io", rect_um=[0.0, 6065.28, 634.608, 7115.28])],
                        pg=dict(domains=[domain]))

    def ptype(self, part):
        return self.types[self.parts[part]["type"]]

    def rect(self, part):
        x, y = self.parts[part]["origin_um"]
        w, h = self.ptype(part)["outline_um"]
        return (x, y, x + w, y + h)

    def to_die(self, part, pt):
        x, y = self.parts[part]["origin_um"]
        return (x + pt[0], y + pt[1])

    def to_type(self, part, pt):
        x, y = self.parts[part]["origin_um"]
        return (pt[0] - x, pt[1] - y)


def domain(rect=(0.0, 6001.64, 698.248, 7178.92)):
    return dict(name="phy_NW_io_u_lk_N0", nets=["VDDPHY", "VSS"], io=["io_NW_io_u_lk_N0"], rect_um=list(rect),
                bumps=dict(rect_um=[0.0, 6065.28, 634.608, 7115.28], pitch_um=45.0), grid=[])


def test_measured_shape_fails_gen_before_fit():
    P = FakePlan(domain())
    with pytest.raises(ValueError, match="holds no macro"):
        GP.phy_pg_domains(P, "q_su21")
    with pytest.raises(ValueError, match="u_ep_N0 straddles"):
        GP.phy_pg_domains(P, "NW_io")


def test_fit_clips_to_partition_and_cuts_at_endpoint():
    d = domain()
    r, part, steps = F.fit_domain(FakePlan(d), d)
    assert part == "NW_io"
    assert r == [0.0, 6065.28, 648.0, 7153.92]
    assert [s["cut"] for s in steps] == ["partition", "block"] and steps[1]["inst"] == "u_ep_N0"
    P = FakePlan(dict(d, rect_um=r))
    assert GP.phy_pg_domains(P, "q_su21") == []
    got = GP.phy_pg_domains(P, "NW_io")
    assert got[0][4] == ["u_lk_N0"] and got[0][3] == [0.0, 0.0, 648.0, 1088.64]


def test_fitted_domain_is_a_fixed_point():
    d = domain((0.0, 6065.28, 648.0, 7153.92))
    r, _, steps = F.fit_domain(FakePlan(d), d)
    assert r == [0.0, 6065.28, 648.0, 7153.92] and steps == []


def test_fail_closed_when_a_cut_would_drop_the_bump_field():
    # endpoint pushed into the bump field: no cut can keep the bumps covered
    d = domain()
    with pytest.raises(ValueError, match="no cut keeps"):
        F.fit_domain(FakePlan(d, ep_y=1000.0), d)


def test_fail_closed_without_a_macro_inside():
    d = domain()
    P = FakePlan(d)
    P.types["NW_io"]["contents"] = P.types["NW_io"]["contents"][1:]
    with pytest.raises(ValueError, match="holds no placed block"):
        F.fit_domain(P, d)


def test_fail_closed_on_unknown_window_partition():
    d = domain()
    P = FakePlan(d)
    P.die["io"][0]["part"] = "nowhere"
    with pytest.raises(ValueError, match="exactly one known partition"):
        F.fit_domain(P, d)


def test_split_phy_glue_parent_is_judged_by_its_sub_cores():
    """HBM u_lk_N0 (ot_pdie_serdes, wires-only glue, no lef) over hard sub-cores u_lk_N0.u_fcore.u_core.u_tx/...:
    the domain powers the sub-cores; the glue parent is not a powered macro (it has no view of its own)."""
    d = domain((0.0, 6065.28, 648.0, 7153.92))
    P = FakePlan(d)
    P.types["NW_io"]["hard_cores"] = [
        dict(inst="u_lk_N0__tx", module="ot_pdie_serdes_tx", origin_um=[345.6, 475.2], outline_um=[285.12, 207.36],
             physical_inst="u_lk_N0.u_fcore.u_core.u_tx", physical_master="ot_pdie_serdes_tx"),
        dict(inst="u_lk_N0__chn", module="ot_s81_kp4_dchn", origin_um=[51.84, 138.24], outline_um=[276.48, 138.24],
             physical_inst="u_lk_N0.u_fcore.u_core.u_chn", physical_master="ot_s81_kp4_dchn")]
    got = GP.phy_pg_domains(P, "NW_io")
    assert got[0][4] == ["u_lk_N0.u_fcore.u_core.u_chn", "u_lk_N0.u_fcore.u_core.u_tx"]
    # without sub-cores the same content is a powered macro as before
    P.types["NW_io"]["hard_cores"] = []
    assert GP.phy_pg_domains(P, "NW_io")[0][4] == ["u_lk_N0"]
    # a glue parent that carries its own lef stays a macro
    P.types["NW_io"]["hard_cores"] = [dict(inst="u_lk_N0__tx", module="m", origin_um=[345.6, 475.2],
                                           outline_um=[285.12, 207.36], sub_core_parent="u_lk_N0")]
    P.types["NW_io"]["contents"][0]["lef"] = "x.lef"
    assert GP.phy_pg_domains(P, "NW_io")[0][4] == ["u_lk_N0", "u_lk_N0__tx"]
