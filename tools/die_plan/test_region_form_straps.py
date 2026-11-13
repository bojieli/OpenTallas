"""QC-REGION-1 11-13 (s29 strict bind: 'declare count strap strap_ca_k_bc_i20[7] in types[].count_straps'): the step
that writes K / DEPTH also sizes types[].count_straps (region_form.sync_count_straps), for any ring choice."""
import pytest
import count_align_bind as CAB
import region_form as RF
from clock_landings import Landings, LandingError
from test_count_straps import strap_vehicle
from test_clock_landings import B_BODY


def kstrap(p, name="strap_ca_k_y"):
    return next(x for x in p["partition_types"]["B"]["count_straps"] if x["name"] == name)


def test_k_past_2n_minus_1_and_depth8_widen_the_strap_and_landings_pass():
    p, t = strap_vehicle()
    Landings(p, t)                                        # D4: 6-bit strap declared and required
    # re-planned ring: DEPTH 4 -> 8, K grows past 2^6 - 1
    t["count_aligned"]["ports"]["P"].update(depth=8, K=70)
    with pytest.raises(LandingError, match=r"strap_ca_k_y\[7\]"):
        Landings(p, t)
    led = RF.sync_count_straps(p, t["count_aligned"])
    assert led == [dict(type="B", strap="strap_ca_k_y", old=6, new=7, sites_added=[], sites_dropped=[])]
    assert kstrap(p)["width"] == 7
    c = Landings(p, t)                                    # 0 landing errors
    st = CAB.strap_ties(t["count_aligned"], p)
    assert st["instances"]["b"]["values"]["strap_ca_k_y"] == CAB.strap_bits(70, 7) == 70
    assert "input wire [6:0] strap_ca_k_y" in c.type_rtl("B", B_BODY)
    assert RF.strap_summary(led) == dict(straps=1, types=1, widened=1, narrowed=0, width_change={"6->7": 1})
    assert RF.sync_count_straps(p, t["count_aligned"]) == []          # idempotent


def test_depth16_ring_choice_goes_through_the_same_widening():
    p, t = strap_vehicle()
    t["count_aligned"]["ports"]["P"]["depth"] = 16
    t["count_aligned"]["ports"]["Q"]["depth"] = 16
    led = RF.sync_count_straps(p, t["count_aligned"])
    assert [(r["old"], r["new"]) for r in led] == [(6, 8)]
    Landings(p, t)


def test_sites_kept_widened_bits_get_new_sites_and_narrowing_drops_top_bits(monkeypatch):
    p, t = strap_vehicle()
    old = [[4.32 * i, 8.64] for i in range(6)]
    for x in p["partition_types"]["B"]["count_straps"]:
        x["layer"] = "M5"
        x["sites_um"] = old if x["name"] == "strap_ca_k_y" else [[0.0, 4.32 * len(x["name"])]]
    seen = {}

    def free(raw, plan_path, tn, need, taken, cache=None):
        seen.update(tn=tn, need=need, taken=set(taken))
        return [[99.0 + i, 1.0] for i in range(need)]
    monkeypatch.setattr(RF, "_strap_lattice_free", free)
    t["count_aligned"]["ports"]["P"]["depth"] = 8
    led = RF.sync_count_straps(p, t["count_aligned"], "plan.json")
    assert seen["tn"] == "B" and seen["need"] == 1 and {tuple(s) for s in old} <= seen["taken"]
    assert kstrap(p)["sites_um"] == old + [[99.0, 1.0]] and led[0]["sites_added"] == [[99.0, 1.0]]
    Landings(p, t)
    # back to D4 (e.g. a later retime): equal width is required, the top bit and its site go
    t["count_aligned"]["ports"]["P"]["depth"] = 4
    led = RF.sync_count_straps(p, t["count_aligned"], "plan.json")
    assert [(r["old"], r["new"], r["sites_dropped"]) for r in led] == [(7, 6, [[99.0, 1.0]])]
    assert kstrap(p)["sites_um"] == old
    Landings(p, t)


def test_no_strap_form_is_a_noop_and_undeclared_strap_is_a_conflict():
    p, t = strap_vehicle(strap_form=False)
    t["count_aligned"]["ports"]["P"]["depth"] = 8
    assert RF.sync_count_straps(p, t["count_aligned"]) == []
    p, t = strap_vehicle()
    p["partition_types"]["B"]["count_straps"] = [x for x in p["partition_types"]["B"]["count_straps"]
                                                 if x["name"] != "strap_ca_pad"]
    with pytest.raises(RF.Conflict, match="strap_ca_pad"):
        RF.sync_count_straps(p, t["count_aligned"])


def test_plan_only_site_rule_avoids_macros_reserved_sites_and_placed_straps():
    raw = dict(partition_types=dict(T=dict(
        outline_um=[100.0, 100.0],
        hard_cores=[dict(inst="m", origin_um=[0.0, 0.0], outline_um=[30.0, 100.0], orient="R0")],
        clock=dict(tap_um=[51.84, 51.84], reserved_sites_um=[dict(kind="x", rect_um=[60.0, 40.0, 70.0, 60.0])]))))
    taken = [(51.84, 51.84), (47.52, 51.84)]
    got = RF._strap_lattice_free(raw, None, "T", 40, taken)
    assert len(got) == 40 and len({tuple(s) for s in got}) == 40
    for x, y in got:
        assert x > 35.4                                   # macro 0..30 + 5.4 um
        assert not (58.92 <= x <= 71.08 and 38.92 <= y <= 61.08)   # reserved + 1.08 um
        assert all(abs(x - a) >= 2.16 or abs(y - b) >= 2.16 for a, b in taken)
        assert abs(x / RF.STRAP_PITCH_UM - round(x / RF.STRAP_PITCH_UM)) < 1e-6
    assert got[0] in ([56.16, 51.84], [51.84, 47.52], [51.84, 56.16])      # nearest the tap anchor first
    with pytest.raises(RF.Conflict, match="sit on a macro"):
        RF._strap_lattice_free(raw, None, "T", 1, [(8.64, 8.64)])
