"""DIE-QC-11: --tree-opt dme_feed_centroid=1 (opt-in).  The feed of a DME region ends at the centroid of its taps, not at
its partition bbox centre, so a region stretched by one far partition (QC c_W5_bf_01 + io_serdes_2) is not fed past its
cores and back.  Default unchanged; non-DME regions keep the bbox centre."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_link_fishbone import _P, REG, FEED
from test_die_trial_link_htree import TAPS


def _feed_end(n, r):
    return next((d["x"], d["y"]) for d in n.values() if d.get("region_root") == r)


def test_default_unchanged():
    a = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, dme_only={"B"})
    b = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, dme_only={"B"}, dme_feed_centroid=0.0)
    assert a == b


def test_dme_region_feed_ends_at_tap_centroid():
    rr = [r for r in sorted(set(REG.values())) if r != FEED["root"]]
    dme = rr[0]
    n0 = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, dme_only={dme})
    n1 = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, dme_only={dme}, dme_feed_centroid=1.0)
    tl = [t for t in TAPS if REG[t[0]] == dme]
    cx, cy = sum(t[2] for t in tl) / len(tl), sum(t[3] for t in tl) / len(tl)
    x, y = _feed_end(n1, dme)
    assert abs(x - cx) < 1e-3 and abs(y - cy) < 1e-3
    # the root region and every non-DME region keep their bbox-centre feed end
    for r in set(REG.values()) - {dme}:
        assert _feed_end(n0, r) == _feed_end(n1, r)
    # feed legs stay Manhattan (straight M8/M9 legs with corner nodes)
    for d in n1.values():
        if d["parent"] is not None:
            p = n1[d["parent"]]
            assert abs(p["x"] - d["x"]) < 1e-6 or abs(p["y"] - d["y"]) < 1e-6


def test_needs_dme_only():
    a = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0)
    b = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, dme_feed_centroid=1.0)
    assert a == b


def test_centroid_all_regions_keeps_feed_when_region_leaves_dme():
    """S81-REGTREE-1: dme_feed_centroid=2 -> a region moved from DME to the local H-tree keeps its centroid feed end,
    so every feed end equals the all-DME build; with =1 that region falls back to its bbox centre (unchanged)."""
    rr = [r for r in sorted(set(REG.values())) if r != FEED["root"]]
    allr, one = set(rr), rr[0]
    n_all = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, dme_only=allr, dme_feed_centroid=1.0)
    n_ht = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, dme_only=allr - {one},
                                 dme_feed_centroid=2.0)
    for r in set(REG.values()):
        assert _feed_end(n_all, r) == _feed_end(n_ht, r)
    # every region in DME: =2 builds the same tree as =1 (byte-identical)
    assert n_all == D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, dme_only=allr,
                                          dme_feed_centroid=2.0)
