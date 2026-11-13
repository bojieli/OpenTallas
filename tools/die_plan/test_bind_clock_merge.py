"""bind.py asbuilt clock_merge (EDGE-CLOCK-LATE, QC coll_s): related die clock roots of one source that a partition
takes from one family bind to that family; no-op for partitions or domains asbuilt does not name."""
import collections
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402


def _binder(merge):
    return SimpleNamespace(ab={"clock_merge": merge} if merge is not None else {},
                           clk_dom=collections.defaultdict(set))


def _clk(b, p, dom):
    cnt = collections.Counter()
    r = bind.Binder._src_desc(b, p, ("clock", dom), cnt, "ci", "pn", 0)
    return r, cnt


def test_merged_domain_binds_to_family():
    b = _binder({"u_coll_s": {"clk_coll": "clk", "clk_serdes": "clk"}})
    for d in ("clk_coll", "clk_serdes", "clk"):
        r, cnt = _clk(b, "u_coll_s", d)
        assert r == ("clk", "clk") and cnt["clock"] == 1
    assert b.clk_dom["u_coll_s"] == {"clk"}


def test_other_partition_and_domain_unchanged():
    b = _binder({"u_coll_s": {"clk_coll": "clk"}})
    assert _clk(b, "u_coll_n", "clk_coll")[0] == ("clk", "clk_coll")
    assert _clk(b, "u_coll_s", "clk_coll_blk")[0] == ("clk", "clk_coll_blk")
    assert b.clk_dom["u_coll_n"] == {"clk_coll"} and b.clk_dom["u_coll_s"] == {"clk_coll_blk"}


def test_no_key_is_noop():
    for m in (None, {}):
        b = _binder(m)
        assert _clk(b, "p", "clk_serdes")[0] == ("clk", "clk_serdes")
