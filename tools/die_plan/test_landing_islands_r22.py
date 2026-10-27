"""CLOCK-KV-R22: declared die-top data landing islands (landing_islands.py)."""
import copy

import landing_islands as LI

T = dict(module="m", outline_um=[864.0, 1520.64], hard=True,
         ft_slots=[dict(name="ft0", in_face="N", out_face="S", width=1, stations=4)],
         clock=dict(die_islands_um=[[171.18, 21.87, 173.61, 22.68]]))
DEM = dict(source="t", sha256="a" * 64, ff_hold_ps=-109.606, demand_ps=109.606)


def _raw(isl):
    t = copy.deepcopy(T)
    t["landing_islands"] = isl
    return dict(partition_types=dict(kv3_phy_v1=t))


def test_propose_kv_ft0_island_is_legal():
    i = LI.propose(T, "ft0_i", [431.7921, 432.1281], 2, 3, DEM)
    assert i["rect_um"] == [430.704, 1519.29, 433.134, 1520.1]
    assert i["cells"] == {"HB4xp67_ASAP7_75t_R": 6} and i["owner"] == "die_top"
    assert LI.capacity(i["rect_um"], "HB4xp67_ASAP7_75t_R") == 15
    assert LI.check(_raw([i])) == []


def test_check_rejects_bad_islands():
    i = LI.propose(T, "ft0_i", [431.7921, 432.1281], 2, 3, DEM)
    far = dict(i, rect_um=[430.704, 1500.03, 433.134, 1500.84])
    assert any("from the N face" in e for e in LI.check(_raw([far])))
    off = dict(i, rect_um=[430.7, 1519.29, 433.134, 1520.1])
    assert any("off the site/row grid" in e for e in LI.check(_raw([off])))
    clk = dict(i, port="ft0_i", rect_um=[171.18, 21.87, 173.61, 22.68])
    errs = LI.check(_raw([clk]))
    assert any("overlaps die clock island" in e for e in errs)
    short = dict(i, cells={"HB4xp67_ASAP7_75t_R": 5})
    assert any("!= demand bits x k" in e for e in LI.check(_raw([short])))
    own = dict(i, owner="partition")
    assert any("owner must be die_top" in e for e in LI.check(_raw([own])))
    nosha = dict(i, demand=dict(i["demand"], sha256=None))
    assert any("lacks the source sha256" in e for e in LI.check(_raw([nosha])))
    out = dict(i, port="ft0_o")
    assert any("not an input ft slot" in e for e in LI.check(_raw([out])))
    big = dict(i, cells={"HB4xp67_ASAP7_75t_R": 30}, demand=dict(i["demand"], bits=10, k=3))
    assert any("capacity 15" in e for e in LI.check(_raw([big])))
    assert any("overlaps landing island" in e for e in LI.check(_raw([i, dict(i, name="dup")])))


def test_die_islands_outside_outline_fail_and_clip():
    import kv_r22.clip_islands as CI
    raw = _raw([])
    raw["partition_types"]["kv3_phy_v1"]["clock"]["die_islands_um"] = [[-0.54, 21.87, 1.89, 22.68], [171.18, 21.87, 173.61, 22.68]]
    errs = LI.check_die_islands(raw)
    assert len(errs) == 1 and "1 clock.die_islands_um rects outside the outline" in errs[0]
    assert CI.clip([-0.54, 21.87, 1.89, 22.68], 864.0, 1520.64) == [0.0, 21.87, 1.89, 22.68]
    assert CI.clip([862.5, 21.87, 864.6, 22.68], 864.0, 1520.64) == [862.5, 21.87, 864.0, 22.68]
    raw["partition_types"]["kv3_phy_v1"]["clock"]["die_islands_um"][0] = [0.0, 21.87, 1.89, 22.68]
    assert LI.check_die_islands(raw) == []
