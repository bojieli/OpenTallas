"""Unit tests for plan.py: inverse orientation, stage placement, forbidden hard IP, neighbour port alignment."""
import gzip
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import census  # noqa: E402
import geom  # noqa: E402
import plan  # noqa: E402
from test_census import BIG, END, RLY, make_dump  # noqa: E402


def test_inv_xform_roundtrip():
    for o in ("R0", "R180", "MX", "MY", "R90", "R270", "MXR90", "MYR90"):
        X, Y = geom.xform(3, 7, 10, 20, o, 100, 200)
        assert plan.inv_xform(X, Y, 10, 20, o, 100, 200) == (3, 7), o


def test_stage_plan_inout():
    # 9000 um lane, one 2000-um block at 4000..6000, reach 1500
    regs, reps = plan.stage_plan(9000, [("blk", 4000, 6000)], 1500, 450, "inout")
    inb = [t for t, w in regs if w == "blk"]
    assert inb[0] == 4020 and inb[-1] == 5980 and len(inb) == 3     # in, one internal, out
    full = [0] + [t for t, _ in regs] + [9000]
    assert max(b - a for a, b in zip(full, full[1:])) <= 1500 + 1e-6
    full_r = sorted(full + reps)
    assert max(b - a for a, b in zip(full_r, full_r[1:])) <= 450 + 1e-6


def _two_block_die(d, forbid_middle=False):
    # src -> [A][B] -> dst on one row; A and B abut; optional hard-IP block "phy" in the path instead of A
    ms = dict(rly=RLY, big=BIG, end=END, phy_x=(2000, 2000, {}, [("x", "INPUT", 1, "W", 1, 1)]))
    blocks = [("src", "end", 0, 4950), ("dst", "end", 9900, 4950), ("B", "big", 6000, 4000), ("r0", "rly", 3000, 300)]
    blocks.append(("A", "phy_x" if forbid_middle else "big", 4000, 4000))
    bundles = [("src", "q", "r0", "i", 64), ("r0", "o", "dst", "d", 64)]
    make_dump(d, ms, blocks, bundles)


def _run(forbid_middle=False, policy="straight"):
    d = tempfile.mkdtemp()
    o = tempfile.mkdtemp()
    p = tempfile.mkdtemp()
    _two_block_die(d, forbid_middle)
    census.run("synthetic", d, o, png=False, relay_re=r"^rly$", reach_um=1500.0, big_min_um2=1e6)
    js = plan.run("synthetic", os.path.join(o, "synthetic_census.json"), d, p, png=False, relay_re=r"^rly$",
                  forbid_re=r"phy", policy=policy)
    return js, p


def test_plan_neighbour_alignment_and_specs():
    js, p = _run()
    lane = js["lanes"][0]
    assert [s["block"] for s in lane["segments"]] == ["A", "B"]
    a = json.load(open(os.path.join(p, "ftspec", "A.json")))
    b = json.load(open(os.path.join(p, "ftspec", "B.json")))
    ao = [x for x in a["ports"] if x["dir"] == "output"][0]
    bi = [x for x in b["ports"] if x["dir"] == "input"][0]
    assert ao["face"] == "E" and bi["face"] == "W" and ao["layer"] == "M8"
    assert (ao["lo"], ao["hi"]) == (bi["lo"], bi["hi"])                      # abutting ports line up
    assert abs(ao["hi"] - ao["lo"] - 107 * 0.08) < 1e-3                      # ceil(64 / 0.6) tracks
    assert a["variant"] == b["variant"]                                       # identical crossings: one hardening
    assert a["paths"][0]["stages"] == 3 and lane["stages_new"] >= 6
    assert js["summary"]["keep_channel"] == 0


def test_plan_forbidden_hard_ip():
    js, p = _run(forbid_middle=True)
    lane = js["lanes"][0]
    assert all(s["block"] != "A" for s in lane["segments"])
    assert not os.path.exists(os.path.join(p, "ftspec", "A.json"))
