from collections import defaultdict
from types import SimpleNamespace

import native_relay_plan as P


def design(names, positions):
    d = SimpleNamespace(cells={}, cell_in=defaultdict(list), drives=defaultdict(list),
                        nets=[], multi_drv={}, extra={"status": {}})
    for i, (name, x) in enumerate(zip(names, positions)):
        d.cells[i] = ("S", "DFF", x, 0, x + 1, 1, name)
        if i:
            n = len(d.nets)
            d.nets.append(("SIGNAL", ("i", i - 1, False), [("i", i, False)]))
            d.cell_in[i].append((n, False))
            d.drives[i - 1].append(n)
    d.kind = lambda c: d.cells[c][0]
    return d


def test_exact_post_ring_capture_and_wrong_bus_control():
    names = ["u_bound.u_cland_a/u_ring/y", "u_bound.u_bin_a/q"]
    d = design(names, [10, 1800])
    r = P.build(d, {"a"}, False)
    assert len(r["moves"]) == 1
    assert r["moves"][0]["target_center_um"] == [10.5, .5]
    d.cells[0] = (*d.cells[0][:-1], "u_bound.u_cland_other/u_ring/y")
    r = P.build(d, {"a"}, False)
    assert not r["moves"] and len(r["rejected"]) == 1


def test_existing_transport_stages_and_capacity_control():
    names = [f"native.r{i}" for i in range(9)]
    d = design(names, [0] * 8 + [1600])
    r = P.build(d, set())
    assert len(r["relay_chains"]) == 1 and len(r["moves"]) == 7
    assert r["relay_chains"][0]["stage_names"] == names
    assert r["relay_chains"][0]["bounded_site_hop_um"] == 250
    d = design(names[:3], [0, 0, 1600])
    r = P.build(d, set())
    assert not r["moves"] and "insufficient" in r["rejected"][0]["reason"]


def test_branch_observation_and_fixed_stage_are_anchors():
    d = design([f"native.r{i}" for i in range(9)], [0] * 8 + [1600])
    # A live output port makes this register observable; its location cannot be
    # treated as a freely redistributable interior stage.
    d.nets[d.drives[4][0]][2].append(("p", 0, False))
    d.extra["status"][3] = "FIRM"
    r = P.build(d, set())
    assert all(x["cell_id"] not in (3, 4) for x in r["moves"])


def test_ambiguous_driver_cannot_qualify_a_capture():
    d = design(["u_bound.u_cland_a/u_ring/y", "u_bound.u_bin_a/q"], [0, 1800])
    d.multi_drv[0] = {0, 99}
    r = P.build(d, {"a"}, False)
    assert not r["moves"] and r["rejected"]
