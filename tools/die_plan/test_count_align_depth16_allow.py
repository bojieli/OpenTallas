"""COORD 11-13 11:54 (QC-CLKGATE-1 / QC-REGION-1): DEPTH 16 on an explicit per-crossing allow-list
(count_align_plan --depth16-allow), not a global cap raise."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_plan as CAP  # noqa: E402

T = 833.0


def row(port, s, d, dd, up, dn):
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=0.0, unshared_b_ps=0.0,
                margin_ps=0.0)


def rows():
    # a -> b tree edge + two parallel crossings 9 periods wide (> D8 window, < D16 window)
    return [row("ab", "a", "b", 0, 40, 40), row("w1", "a", "b", 0, 4.5 * T, 4.5 * T),
            row("w2", "a", "b", 0, 4.5 * T, 4.5 * T)]


def run(tmp, allow=None, extra=()):
    fi, fo = tmp / "in.json", tmp / "out.json"
    rs = rows()
    fi.write_text(json.dumps(dict(corners=dict(TT=dict(all=rs), FF=dict(all=rs)))))
    a = [str(fi), "--corner", "TT,FF", "--period", str(T), "--wander-frac", "0", "--out", str(fo)] + list(extra)
    if allow is not None:
        (tmp / "allow.json").write_text(json.dumps(allow))
        a += ["--depth16-allow", str(tmp / "allow.json")]
    rc = CAP.main(a)
    return rc, json.loads(fo.read_text())


def test_allow_list_gives_depth16_only_to_listed_crossings(tmp_path):
    rc, d = run(tmp_path, ["w1"])
    o = {x["port"]: x for x in d["crossings"]}
    assert o["w1"]["depth"] == 16 and o["w1"]["rtl"]["DEPTH"] == 16
    assert o["w2"]["depth"] is None                       # not listed: keeps the DEPTH 8 cap and fails
    assert o["ab"]["depth"] == 4 and d["summary"]["max_depth"] == 8
    assert d["summary"]["depth16_allow"]["depth16"] == 1 and rc == 1
    assert CAP.DEPTH16_ALLOW == frozenset()              # one run only


def test_no_allow_list_is_unchanged(tmp_path):
    rc0, d0 = run(tmp_path)
    rc1, d1 = run(tmp_path, [])
    assert d0["crossings"] == d1["crossings"] and "depth16_allow" not in d0["summary"]
    assert all(o["depth"] in (None, 4, 8) for o in d0["crossings"])


def test_unknown_allow_id_refused(tmp_path):
    with pytest.raises(SystemExit):
        run(tmp_path, ["nope"])
