"""HEAD-94: --region-dme-merge-parts (one DME tree over every partition of a listed region; default byte-identical)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as D


class Site:
    W, H = 4000., 4000.

    def legal(self, q):
        return 0 <= q[0] <= self.W and 0 <= q[1] <= self.H

    def nearest(self, q, axis=None):
        return (min(max(q[0], 0.), self.W), min(max(q[1], 0.), self.H))


# strip S has taps far apart; shim O has one tap next to S's tap s1 (a seam launch / capture pair)
TAPS = [("S", "s0", 100., 100.), ("S", "s1", 2900., 100.), ("S", "s2", 1500., 1900.),
        ("O", "o0", 2950., 120.), ("O", "o1", 3500., 800.)]


def _lca_taps(nodes, root, a, b):
    """taps under the lowest node holding both tap ids a and b"""
    def alltaps(i):
        d = nodes[i]
        return [t[1] for t in d["taps"]] + [x for k in d["kids"] for x in alltaps(k)]
    i = root
    while True:
        nxt = [k for k in nodes[i]["kids"] if a in alltaps(k) and b in alltaps(k)]
        if not nxt:
            return alltaps(i)
        i = nxt[0]


def _tree(**kw):
    nodes, root, _ = D.dme_region_tree(Site(), list(TAPS), delay_rep_um=150., **kw)
    return nodes, root


def test_default_unchanged():
    assert _tree() == _tree(merge_parts=False)


def test_pair_joins_low_when_merged():
    nodes, root = _tree()
    sep = _lca_taps(nodes, root, "s1", "o0")
    nodes, root = _tree(merge_parts=True)
    mer = _lca_taps(nodes, root, "s1", "o0")
    assert sorted(mer) == ["o0", "s1"]          # one shared lowest node holds exactly the seam pair
    assert len(sep) > len(mer)                  # per-partition trees only meet at the partition-root cut


def test_taps_and_identity_kept():
    nodes, root = _tree(merge_parts=True)
    def under(i):
        return [(t[0], t[1]) for t in nodes[i]["taps"]] + [x for k in nodes[i]["kids"] for x in under(k)]
    got = sorted(under(root))
    assert got == sorted((t[0], t[1]) for t in TAPS)
    assert nodes[root]["part_root"] == "O+S"
    assert len(set(under(root))) == len(TAPS)




def test_seam_group_pair_is_its_own_subtree_and_default_unchanged():
    taps = [("S", "t_S__clk_t36", 100., 100.), ("S", "t_S__clk_t1", 2900., 100.), ("S", "t_S__clk_t2", 1500., 1900.),
            ("O", "t_O__clk_t2", 3000., 2900.), ("O", "t_O__clk_t5", 3500., 800.)]
    taps = [(a, b, c, d) for a, b, c, d in taps]
    base, rb, _ = D.dme_region_tree(Site(), list(taps), delay_rep_um=150.)
    nodes, root, _ = D.dme_region_tree(Site(), list(taps), delay_rep_um=150.,
                                       seam_groups=[["S/clk_t36", "O/clk_t2"]])
    def under(n, i):
        return [t[1] for t in n[i]["taps"]] + [x for k in n[i]["kids"] for x in under(n, k)]
    assert sorted(under(nodes, root)) == sorted(t[1] for t in taps)
    # the seam pair sits under one node holding exactly those two taps
    found = [i for i in range(len(nodes)) if sorted(under(nodes, i)) == ["t_O__clk_t2", "t_S__clk_t36"] and nodes[i]["kids"]]
    assert found
    assert D.dme_region_tree(Site(), list(taps), delay_rep_um=150., seam_groups=None)[0] == base
