"""TOK-QC-2: ca_pair_rule - both directions of each collective relay pair get the same count; identity kept; guards kept."""
import json, sys, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ca_pair_rule as PR

T = 833.0


def mk(tx, rx, lhi=1200.0, tree=False):
    b = dict(period_ps=T, ports={}, regions={})
    t = dict(ports=[])
    hops = ["coll_core", "coll_f2", "coll_f1", "coll_s"]
    for i, sl in enumerate(tx):
        p = f"coll_core__crec_tx_s1__{i}"
        b["ports"][p] = dict(K=sl - 1, sched_lat=sl, depth=4, tree=tree, L_lo_ps=lhi - 300, L_hi_ps=lhi,
                             src_part=hops[i], dst_part=hops[i + 1])
        t["ports"].append(dict(port=p, lane="coll_core__crec_tx_s1"))
    for i, sl in enumerate(rx):
        p = f"coll_s__crec_rx_s1__{i}"
        b["ports"][p] = dict(K=sl - 1, sched_lat=sl, depth=4, tree=False, L_lo_ps=lhi - 300, L_hi_ps=lhi,
                             src_part=hops[3 - i], dst_part=hops[2 - i])
        t["ports"].append(dict(port=p, lane="coll_s__crec_rx_s1"))
    return b, t


def tot(b, pre):
    return sum(c["sched_lat"] for p, c in b["ports"].items() if p.startswith(pre))


def test_equalises_short_direction():
    b, t = mk([2, 2, 2], [3, 3, 3])
    rec = PR.apply(b, t)
    assert tot(b, "coll_core__crec_tx_s1") == tot(b, "coll_s__crec_rx_s1") == 9
    assert all(c["K"] + 1 == c["sched_lat"] for c in b["ports"].values())      # identity kept (n_d - n_s = 0 here)
    assert len(rec[0]["steps"]) == 3 and len({s["port"] for s in rec[0]["steps"]}) == 3   # spread, one per hop


def test_equal_pair_unchanged():
    b, t = mk([3, 2, 3], [2, 3, 3])
    b0 = copy.deepcopy(b)
    PR.apply(b, t)
    assert b == b0


def test_guard_violation_fails():
    b, t = mk([2, 2, 2], [3, 3, 3], lhi=3.5 * T - 150)          # +T would cross the high guard
    try:
        PR.apply(b, t)
    except ValueError as e:
        assert "cannot be placed" in str(e)
    else:
        raise AssertionError("must fail")


def test_tree_hop_never_moved():
    b, t = mk([2, 2, 2], [3, 3, 3], tree=True)
    try:
        PR.apply(b, t)
    except ValueError:
        pass
    else:
        raise AssertionError("tree hops must not take a step")


def test_mutant_unequal_detected():
    """mutant: dropping one step leaves the directions unequal (what coll_regen RS_j rejects)"""
    b, t = mk([2, 2, 2], [3, 3, 3])
    rec = PR.apply(b, t)
    p = rec[0]["steps"][0]["port"]
    b["ports"][p]["sched_lat"] -= 1
    assert tot(b, "coll_core__crec_tx_s1") != tot(b, "coll_s__crec_rx_s1")


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("PASS", k)
