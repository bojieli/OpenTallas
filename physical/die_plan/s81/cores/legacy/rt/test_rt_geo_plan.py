#!/usr/bin/env python3
"""rt_geo_plan: spine stays off macros, no hop over the repeater limit except across a macro gap, every sink gets one tap."""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))


def run(rows):
    with tempfile.TemporaryDirectory() as d:
        i, o = d + "/i", d + "/o"
        open(i, "w").write("\n".join("\t".join(map(str, r)) for r in rows) + "\n")
        subprocess.check_call([sys.executable, "-I", HERE + "/rt_geo_plan.py", i, o], stdout=subprocess.DEVNULL)
        return [l.rstrip("\n").split("\t") for l in open(o)]


def test_wall():
    M = (100, 0, 110, 180)  # wall with a gap only above y 180
    rows = [("CORE", 0, 0, 300, 200), ("PORT", 50, 0), ("MACRO",) + M, ("MTAP", "ot_rt_mtap1", 94, 90)]
    rows += [("REG", "a%d" % k, 20 + k % 40, 20 + k % 100) for k in range(60)]
    rows += [("REG", "b%d" % k, 200 + k % 40, 20 + k % 100) for k in range(60)]
    out = run(rows)
    bufs = {r[1]: r for r in out if r[0] == "BUF"}
    for r in bufs.values():
        x, y = float(r[2]), float(r[3])
        assert not (M[0] - 4.6 <= x <= M[2] + 4.6 and M[1] - 4.6 <= y <= M[3] + 4.6), r
    assign = {r[1]: r[2] for r in out if r[0] == "ASSIGN"}
    assert len(assign) == 120
    taps = {r[1] for r in out if r[0] == "TAP"}
    assert "ot_rt_mtap1" in taps and set(assign.values()) <= taps
    # no region tap serves both sides of the wall
    for t in taps:
        s = {k[0] for k, v in assign.items() if v == t}
        assert len(s) <= 1, t
    # parents exist and precede children
    seen = {"ROOT"}
    for r in out:
        if r[0] == "BUF":
            assert r[4] in seen
            seen.add(r[1])
        elif r[0] == "TAP":
            assert r[4] in seen


if __name__ == "__main__":
    test_wall()
    print("PASS")
