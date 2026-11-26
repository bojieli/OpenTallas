"""HEAD-DIECLOCK-PHYFLOOR 11-25: die clock sites honour a type's phy_pg_floor_um (gen_phys PHY region floor): the part of
a die PHY domain rect below the floor of the partition it covers is legal; above it, and on types without the key, the PHY
exclusion is unchanged."""
from types import SimpleNamespace
import die_trial as D


def plan(floor=None, orient_b="R0"):
    def to_die(n, q):
        if n == "a":
            return (q[0], q[1])
        if n == "c":
            return (400 + q[0], q[1])
        return (800 + q[0], q[1]) if orient_b == "R0" else (800 + q[0], 200 - q[1])   # b MX: y mirrored
    tf = {"outline_um": [100, 200], "hard_cores": []}
    if floor is not None:
        tf["phy_pg_floor_um"] = floor
    return SimpleNamespace(
        W=900, H=200,
        parts={"a": {"type": "tf", "origin_um": [0, 0]}, "b": {"type": "tf", "origin_um": [800, 0]},
               "c": {"type": "t", "origin_um": [400, 0]}},
        types={"tf": tf, "t": {"outline_um": [100, 200], "hard_cores": []}},
        die={"channels": [], "pg": {"domains": [
            {"rect_um": [0, 50, 100, 200], "nets": ["VDDPHY", "VSS"]},
            {"rect_um": [800, 0, 900, 150], "nets": ["VDDPHY", "VSS"]},
            {"rect_um": [400, 50, 500, 200], "nets": ["VDDPHY", "VSS"]}]}},
        to_die=to_die)


def test_without_floor_the_whole_domain_is_excluded():
    s = D.SiteMap(plan())
    assert not s.legal((50, 100)) and not s.legal((450, 100))


def test_floor_releases_only_below_it_and_only_on_that_type():
    s = D.SiteMap(plan(floor=120))
    assert s.legal((50, 100))                      # type y 100 < floor 120: core supply
    assert not s.legal((50, 150))                  # above the floor: PHY
    assert not s.legal((50, 121))                  # halo at the new edge
    assert not s.legal((450, 100))                 # type without the key: unchanged


def test_floor_follows_the_instance_orientation():
    s = D.SiteMap(plan(floor=120, orient_b="MX"))  # b mirrored: type y < 120 is die y > 80
    assert s.legal((850, 120))
    assert not s.legal((850, 40))


def test_rect_minus_pieces_cover_the_difference():
    r, c = (0, 0, 10, 10), (2, 3, 6, 20)
    ps = D._rect_minus(r, [c])
    assert sum((q[2] - q[0]) * (q[3] - q[1]) for q in ps) == 100 - 4 * 7
    assert D._rect_minus(r, [(20, 20, 30, 30)]) == [r]
