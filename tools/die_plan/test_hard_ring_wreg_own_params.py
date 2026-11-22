"""HARD-RING-WREG-1: a listed signed hard ring without FREG never takes the type-wide cfg freg."""
import clock_landings as CL

PARAMS = dict(W=300, DEPTH=4, STATUS_REG=1, GUARD_REG=1, WFALL=1, WREG=1, DSREP=8, WRITE_CHUNK=16, RSTREP=11)


def _plan(buses, hard=True, **cfg):
    t = dict(clock=dict(landing_ring_wreg=dict(buses=buses, **cfg)), hard_cores=[])
    if hard:
        t["hard_cores"].append(dict(inst="cl_y", physical_inst="u_bound.u_cland_y",
                                    param_wrap=dict(base="ot_dp_clk_landing_cas", params=dict(PARAMS))))
    return dict(partition_types=dict(B=t))


def test_listed_hard_ring_ignores_shared_freg():
    p = _plan(["x", "y"], dsrep=1, freg=True)
    y = CL.ring_write_reg(p, "B", "y")
    assert y["freg"] is False and y["depth"] == 1
    x = CL.ring_write_reg(p, "B", "x")                     # the soft bus keeps the type cfg
    assert x["freg"] is True and x["depth"] == 2 and x["dsrep"] == 1 and "write_chunk" not in x


def test_matching_cfg_unchanged():
    p = _plan(["y"], dsrep=8, write_chunk=16)
    q = _plan(["y"], hard=False, dsrep=8, write_chunk=16)
    assert CL.ring_write_reg(p, "B", "y") == CL.ring_write_reg(q, "B", "y")


def test_unlisted_hard_ring_unchanged():
    p = _plan(["x"], dsrep=1, freg=True)
    assert CL.ring_write_reg(p, "B", "y") is None


def test_hard_ring_signed_with_freg_keeps_cfg():
    p = _plan(["y"], dsrep=1, freg=True)
    p["partition_types"]["B"]["hard_cores"][0]["param_wrap"]["params"]["FREG"] = 1
    y = CL.ring_write_reg(p, "B", "y")
    assert y["freg"] is True and y["depth"] == 2
