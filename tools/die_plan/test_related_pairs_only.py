"""DIE-LEVEL-CHECK-1119 (FABLE-PD-KV-2300 C): intra pairs of a type with a kit-exported tap-pair list are timed only when
their kit ports carry data; unlisted types stay all-pair and are counted."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_related as R  # noqa: E402


def _taps():
    t = {}
    for part in ("a0", "b0"):
        for k in ("clk", "clk_t1", "clk_t2"):
            t[f"t_{part}__{k}"] = {"part": part, "cppr_node": "n0"}
    return t


PLAN = {"ports": [], "partitions": [{"name": "a0", "type": "A"}, {"name": "b0", "type": "B"}]}


def test_listed_type_keeps_related_pairs_only(tmp_path):
    f = tmp_path / "A.json"
    f.write_text(json.dumps({"related_pairs": {"A": [["clk", "clk_t1"]]}}))
    rel = R.load_related_pairs([str(tmp_path)])
    pairs, cov = R.build_pairs(PLAN, _taps(), related=rel)
    a = sorted((x, y) for x, y, p in pairs["intra"] if p == "a0")
    assert a == [("t_a0__clk", "t_a0__clk_t1"), ("t_a0__clk_t1", "t_a0__clk")]
    assert len([1 for _, _, p in pairs["intra"] if p == "b0"]) == 6      # unlisted type B: all 3x2 ordered pairs
    rp = cov["related_pairs"]
    assert (rp["kept"], rp["dropped"], rp["unlisted"], rp["listed_types"]) == (2, 4, 6, 1)
    assert rp["unlisted_types"] == {"B": 6}


def test_empty_list_drops_every_pair_and_none_is_unchanged(tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"related_pairs": {"A": [], "B": [["clk_t1", "clk_t2"]]}}))
    pairs, cov = R.build_pairs(PLAN, _taps(), related=R.load_related_pairs([str(f)]))
    assert [p for _, _, p in pairs["intra"]].count("a0") == 0
    assert [p for _, _, p in pairs["intra"]].count("b0") == 2
    base, cov0 = R.build_pairs(PLAN, _taps())
    assert len(base["intra"]) == 12 and "related_pairs" not in cov0
