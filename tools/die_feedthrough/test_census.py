"""Unit tests: geometry, lane extraction (chains, taps, reconvergence, side pins), census crossings and face load.
    python3 -m pytest -q tools/die_feedthrough/
"""
import gzip
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import census  # noqa: E402
import geom  # noqa: E402
import lanes  # noqa: E402
from dump_io import Dump  # noqa: E402

LAYERS = [dict(name="M7", dir="VERTICAL", pitch=0.08, width=0.04), dict(name="M8", dir="HORIZONTAL", pitch=0.08,
          width=0.04), dict(name="M9", dir="VERTICAL", pitch=0.08, width=0.04)]


def make_dump(d, masters, blocks, bundles, die=(0, 0, 10000, 10000)):
    """masters: {name: (w, h, obs_cover{L:f}, [(bus, dir, nbits, face, lo, hi)])}; blocks: [(inst, master, x, y)]."""
    json.dump(dict(die=list(die), core=list(die), layers=LAYERS, odb="synthetic"), open(os.path.join(d, "die.json"), "w"))
    with open(os.path.join(d, "masters.tsv"), "w") as f, gzip.open(os.path.join(d, "mpins.tsv.gz"), "wt") as fp:
        for n, (w, h, cov, buses) in masters.items():
            f.write(f"{n}\t{w}\t{h}\t{len(buses)}\tM5:1\t{','.join(cov)}\t"
                    f"{','.join(f'{k}:{v}' for k, v in cov.items())}\n")
            for b, di, nb, face, lo, hi in buses:
                fp.write(f"{n}\t{b}\t{di}\t{nb}\tM5\t{face}\t{lo}\t{hi}\tSIGNAL\n")
    with open(os.path.join(d, "blocks.tsv"), "w") as f:
        for inst, m, x, y in blocks:
            w, h = masters[m][0], masters[m][1]
            f.write(f"{inst}\t{m}\t{x}\t{y}\t{w}\t{h}\tR0\tFIRM\n")
    with gzip.open(os.path.join(d, "bundles.tsv.gz"), "wt") as f:
        for si, sb, di, db, bits in bundles:
            f.write(f"{si}\t{sb}\t{di}\t{db}\t{bits}\t1\t{bits}\tSIGNAL\n")


RLY = (20, 20, {}, [("i", "INPUT", 64, "W", 10, 10), ("o", "OUTPUT", 64, "E", 10, 10), ("ck", "INPUT", 1, "S", 5, 5),
                    ("rs", "INPUT", 1, "S", 6, 6)])
BIG = (2000, 2000, {"M8": 1.0}, [("x", "INPUT", 64, "W", 1000, 1000), ("y", "OUTPUT", 64, "E", 1000, 1000)])
END = (100, 100, {}, [("q", "OUTPUT", 64, "E", 50, 50), ("d", "INPUT", 64, "W", 50, 50)])


def test_xform_orients():
    assert geom.xform(1, 2, 10, 20, "R0") == (1, 2)
    assert geom.xform(1, 2, 10, 20, "MY") == (9, 2)
    assert geom.xform(1, 2, 10, 20, "MX") == (1, 18)
    assert geom.xform(1, 2, 10, 20, "R180") == (9, 18)


def test_seg_crossings_faces():
    rects = [("b", 100, 100, 200, 200)]
    c = geom.seg_crossings((0, 150), (500, 150), rects)
    assert c == [("b", 200, "W", "E", 100, 300)]
    c = geom.seg_crossings((150, 500), (150, 0), rects)
    assert c[0][2:4] == ("N", "S")
    assert geom.seg_crossings((0, 50), (500, 50), rects) == []


def test_ideal_stages():
    assert geom.ideal_stages(900, 1000) == 0
    assert geom.ideal_stages(1000, 1000) == 0
    assert geom.ideal_stages(2500, 1000) == 2
    assert geom.stage_positions(3000, 2) == [1000, 2000]


def test_relay_pairs_named_and_fallback():
    with tempfile.TemporaryDirectory() as d:
        make_dump(d, dict(r=RLY, z=(20, 20, {}, [("dd", "INPUT", 8, "W", 1, 1), ("qq", "OUTPUT", 8, "E", 1, 1),
                                                   ("ck", "INPUT", 1, "S", 1, 1)])), [], [])
        D = Dump(d)
        assert lanes.relay_pairs(D.masters["r"]) == [("i", "o")]
        assert lanes.relay_pairs(D.masters["z"]) == [("dd", "qq")]


def _chain_dump(d, n=4, extra=()):
    blocks = [("src", "end", 0, 4950), ("dst", "end", 9000, 4950), ("blk", "big", 4000, 4000)]
    bundles = []
    prev = ("src", "q")
    for k in range(n):
        blocks.append((f"r{k}", "rly", 500 + k * 2000, 300))
        bundles.append((prev[0], prev[1], f"r{k}", "i", 64))
        bundles.append(("rstgen", "o", f"r{k}", "rs", 1))      # side pin: not a lane
        prev = (f"r{k}", "o")
    bundles.append((prev[0], prev[1], "dst", "d", 64))
    bundles.extend(extra)
    make_dump(d, dict(rly=RLY, big=BIG, end=END), blocks, bundles)


def test_extract_chain():
    with tempfile.TemporaryDirectory() as d:
        _chain_dump(d)
        D = Dump(d)
        groups, rm, st = lanes.extract(D, r"^rly$")
        g = [x for x in groups if x["src"] == "src"]
        assert len(g) == 1 and g[0]["dst"] == "dst" and g[0]["bits"] == 64 and g[0]["stages_max"] == 4
        assert g[0]["path"] == ("r0", "r1", "r2", "r3")
        assert st["n_relays_on_lanes"] == 4


def test_extract_tap_and_reconverge():
    # src -> r0 ; r0 taps 32 bits to dst and 32 bits to r1 -> dst  (reconvergent: bits = 64, not double counted)
    with tempfile.TemporaryDirectory() as d:
        blocks = [("src", "end", 0, 0), ("dst", "end", 5000, 0), ("r0", "rly", 1000, 0), ("r1", "rly", 2000, 0),
                  ("flt", "end", 0, 3000)]
        bundles = [("src", "q", "r0", "i", 64), ("r0", "o", "dst", "d", 32), ("r0", "o", "r1", "i", 32),
                   ("r1", "o", "dst", "d", 32), ("flt", "q", "r1", "i", 1)]
        make_dump(d, dict(rly=RLY, end=END), blocks, bundles)
        groups, _, _ = lanes.extract(Dump(d), r"^rly$")
        g = {(x["src"], x["dst"]): x for x in groups}
        assert g[("src", "dst")]["bits"] == 64
        assert g[("src", "dst")]["stages_max"] == 2 and g[("src", "dst")]["stages_min"] == 1
        assert g[("flt", "dst")]["bits"] == 1        # a 1-bit merge is not credited with the trunk width


def test_census_crossing_and_load():
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as o:
        _chain_dump(d)
        js = census.run("synthetic", d, o, png=False, relay_re=r"^rly$", reach_um=1500.0, big_min_um2=1e6,
                        ft_layers=("M8", "M9"))
        s = js["summary"]
        assert s["lane_groups"] == 1 and s["bits"] == 64
        g = js["groups"][0]
        # straight route src (100, 5000) -> dst (9000, 5000) crosses blk W->E
        assert [c["block"] for c in g["crosses"]] == ["blk"]
        assert g["crosses"][0]["face_in"] == "W" and g["crosses"][0]["face_out"] == "E"
        assert g["ideal_stages"] == 5 and g["stages"] == 4
        b = [x for x in js["blocks"] if x["inst"] == "blk"][0]
        assert b["ft_blocked"] is True
        assert b["faces"]["W"]["bits"] == 64 and b["faces"]["W"]["tracks"] == 25000    # 2000 um / 0.08 on M8
        assert b["stages_in"] == 1


def test_merge_regions():
    from dump_io import Inst
    a = [Inst("a", "m", 0, 0, 10, 10), Inst("b", "m", 15, 0, 10, 10), Inst("c", "m", 100, 0, 10, 10)]
    regs = census.merge_regions(a, 6.0)
    sizes = sorted(len(m) for _, m in regs)
    assert sizes == [1, 2]
