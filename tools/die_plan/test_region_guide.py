"""FLOW-23 (COORD 11-02 23:0x, GEOM-111 class D): region_guide.py soft GPL region guides -- small fixtures, no docker."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import region_guide as RG  # noqa: E402
import geom_rules as G  # noqa: E402


def fixture(tmp_path, bits=4, bcast=0, face=True):
    """400x400 die: bit i launch rd_q[i] at the W edge, capture up_d[i] at the E edge (one logic cell between),
    distance > 405 for every bit; optional pin register (in_p -> u_bin/q at the W face -> far capture) and a broadcast
    register driving `bcast` far captures."""
    L, cid, nets, pins = [], [0], [], []

    def cell(kind, x, y, name, master="DFF"):
        cid[0] += 1
        L.append(f"C\t{cid[0]}\t{kind}\t{master}\t{x}\t{y}\t{x + 1}\t{y + 0.27}\t{name}")
        return cid[0]

    def net(drv, *sinks):
        nets.append("\t".join(["N", "SIGNAL", drv] + list(sinks)))

    for i in range(bits):
        a = cell("S", 10, 20 + 10 * i, f"u_core.rd_q\\[{i}\\]$_DFF_P_")
        g = cell("L", 200, 200, f"u_core.cloud_{i}", "AND2")
        b = cell("S", 389, 370 - 10 * i, f"u_core.up_d\\[{i}\\]$_DFF_P_")
        net(f"i{a}", f"i{g}")
        net(f"i{g}", f"i{b}")
    if face:
        pins.append("P\t0\tin_p\tINPUT\tSIGNAL\tM4\t0\t300")
        f = cell("S", 2, 300, "u_bin/q$_DFF_P_")
        x = cell("S", 380, 10, "u_core.far$_DFF_P_")
        net("p0", f"i{f}")
        net(f"i{f}", f"i{x}")
    if bcast:
        s = cell("S", 5, 5, "u_core.post$_DFF_P_")
        caps = [cell("S", 390, 395 - i, f"u_core.op\\[{i}\\]$_DFF_P_") for i in range(bcast)]
        net(f"i{s}", *[f"i{c}" for c in caps])
    pins.append("P\t1\tclk\tINPUT\tCLOCK\tM5\t200\t0")
    txt = "\n".join(["D\t0\t0\t400\t400", "R\t4\t4\t396\t396"] + L + pins + nets) + "\n"
    p = tmp_path / "geom.tsv"
    p.write_text(txt)
    return G.Design(str(p))


def test_bit_slices_guided_under_reach(tmp_path):
    D = fixture(tmp_path)
    before = G.r2r_metrics(D)
    assert before["r2r_captures_gt405"] == 5          # 4 bit slices + the pin-register pair
    s = RG.plan(D)
    assert s["class_d"] and s["tile_um"] == (405 - 45) / 2
    assert s["predicted"]["r2r_captures_gt405"] == 0 and s["predicted"]["r2r_max"] <= 405
    guided = {n for r in s["regions"] for n in r["insts"]}
    for i in range(4):
        assert f"u_core.rd_q\\[{i}\\]$_DFF_P_" in guided and f"u_core.up_d\\[{i}\\]$_DFF_P_" in guided
    # same slice -> same region
    reg_of = {n: r["name"] for r in s["regions"] for n in r["insts"]}
    assert all(reg_of[f"u_core.rd_q\\[{i}\\]$_DFF_P_"] == reg_of[f"u_core.up_d\\[{i}\\]$_DFF_P_"] for i in range(4))
    # regions disjoint and inside the core
    bx = [r["box_um"] for r in s["regions"]]
    for k, a in enumerate(bx):
        assert 4 - 1e-6 <= a[0] < a[2] <= 396 + 1e-6 and 4 - 1e-6 <= a[1] < a[3] <= 396 + 1e-6
        assert (a[2] - a[0]) + (a[3] - a[1]) <= 405 - 45 + 1e-6
        for b in bx[k + 1:]:
            assert not (a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3])


def test_pin_register_never_guided_but_anchors_its_slice(tmp_path):
    s = RG.plan(fixture(tmp_path))
    guided = {n for r in s["regions"] for n in r["insts"]}
    assert "u_bin/q$_DFF_P_" not in guided and "u_bin/q$_DFF_P_" in s["fixed_skipped"]
    # the movable capture goes to the slice's Manhattan minimax centre: within reach of the fixed face register
    r = next(r for r in s["regions"] if "u_core.far$_DFF_P_" in r["insts"])
    b = r["box_um"]
    assert 134 < (b[0] + b[2]) / 2 < 266 and 134 < (b[1] + b[3]) / 2 < 266      # the centre tile, not a face
    assert max(abs(x - 2.5) for x in (b[0], b[2])) + max(abs(y - 300.135) for y in (b[1], b[3])) <= 405


def test_boxes_small_and_off_macros(tmp_path):
    # GPL removes region area from the top level: boxes are sized by member area, never a whole tile
    s = RG.plan(fixture(tmp_path))
    for r in s["regions"]:
        b = r["box_um"]
        assert (b[2] - b[0]) * (b[3] - b[1]) <= max(RG.BOX_MIN_SIDE ** 2, len(r["insts"]) * 0.27 / RG.BOX_DENSITY) + 1e-6
    tile = (4, 4, 134, 134)
    b = RG.guide_box(tile, (60, 60), 10.0, [(40, 40, 80, 80)])
    assert not (b[0] < 80 and 40 < b[2] and b[1] < 80 and 40 < b[3]) and tile[0] <= b[0] and b[2] <= tile[2]


def test_broadcast_left_to_its_class(tmp_path):
    s = RG.plan(fixture(tmp_path, bits=2, bcast=20, face=False))
    guided = {n for r in s["regions"] for n in r["insts"]}
    assert "u_core.post$_DFF_P_" in s["broadcast_skipped"] and "u_core.post$_DFF_P_" not in guided
    assert not any(n.startswith("u_core.op") for n in guided)
    assert s["pair_census"]["guided"]["predicted_gt_limit"] == 0
    assert s["pair_census"]["broadcast"]["pairs"] == 20


def test_no_class_d_no_regions(tmp_path):
    s = RG.plan(fixture(tmp_path, bits=0, face=False))
    assert not s["class_d"] and s["regions"] == [] and s["pairs"] == []


def test_class_d_reads_auto_geom_rules():
    assert RG.class_d({"rules": [{"rule": "r2r", "status": "FAIL"}]})
    assert RG.class_d({"rules": [{"rule": "r2r_count", "status": "FAIL"}]})
    assert not RG.class_d({"rules": [{"rule": "r2r", "status": "PASS"}, {"rule": "pin_reg", "status": "FAIL"}]})


def _kit(tmp_path):
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "face_flops.tcl").write_text("# hook\n")
    (kd / "face_flops_release.tcl").write_text("# release\n")
    return kd


def test_install_writes_hook_and_sources_it_last(tmp_path):
    s = RG.plan(fixture(tmp_path))
    kd = _kit(tmp_path)
    rec = RG.install(kd, s, outline=(400, 400), src=dict(file="x"))
    assert rec["regions"] == len(s["regions"]) and rec["insts"] == sum(len(r["insts"]) for r in s["regions"])
    ff = (kd / "face_flops.tcl").read_text().splitlines()
    assert ff[-1] == "source [file join [file dirname [info script]] region_guide.tcl]"
    assert (kd / "face_flops_release.tcl").read_text().splitlines()[-1].endswith("region_guide_release.tcl]")
    tsv = (kd / "region_guide.tsv").read_text().splitlines()
    assert sum(1 for x in tsv if x.startswith("R\t")) == len(s["regions"])
    # exact ODB names (escaped brackets) are kept verbatim
    assert "I\t" + s["regions"][0]["name"] + "\t" + s["regions"][0]["insts"][0] in tsv
    assert "dbRegion_create" in (kd / "region_guide.tcl").read_text()
    assert "dbRegion_destroy" in (kd / "region_guide_release.tcl").read_text()
    assert json.loads((kd / "region_guide.json").read_text())["schema"] == RG.SCHEMA


def test_install_refuses_stale_or_empty(tmp_path):
    s = RG.plan(fixture(tmp_path))
    with pytest.raises(SystemExit, match="stale"):
        RG.install(_kit(tmp_path), s, outline=(345.6, 518.4))
    e = dict(s, regions=[])
    kd2 = tmp_path / "k2"
    kd2.mkdir()
    (kd2 / "face_flops.tcl").write_text("")
    (kd2 / "face_flops_release.tcl").write_text("")
    with pytest.raises(SystemExit, match="no regions"):
        RG.install(kd2, e, outline=(400, 400))
    over = dict(s, regions=[dict(name="ot_rg_0_0", box_um=[4, 4, 100, 100], insts=["a"]),
                            dict(name="ot_rg_0_1", box_um=[50, 50, 150, 150], insts=["b"])])
    with pytest.raises(SystemExit, match="overlaps"):
        RG.install(kd2, over, outline=(400, 400))


def test_cli_plan_only_on_class_d(tmp_path):
    gd = tmp_path / "geom"
    gd.mkdir()
    fixture(gd)
    out = tmp_path / "spec.json"
    (gd / "auto_geom.json").write_text(json.dumps({"rules": [{"rule": "r2r", "status": "PASS"}], "line": "x"}))
    assert RG.main(["plan", "--geom-dir", str(gd), "--out", str(out)]) == 0 and not out.exists()
    (gd / "auto_geom.json").write_text(json.dumps({"rules": [{"rule": "r2r", "status": "FAIL"}], "line": "x"}))
    assert RG.main(["plan", "--geom-dir", str(gd), "--out", str(out)]) == 0 and out.exists()
    s = json.loads(out.read_text())
    assert s["regions"] and s["source"]["geom_tsv_sha256"]
    assert RG.main(["measure", "--geom-dir", str(gd), "--spec", str(out)]) == 0


def test_tcl_hook_skips_fixed_and_grouped():
    t = RG.TCL_HOOK.read_text()
    assert "FIRM LOCKED COVER" in t and "getGroup" in t and "isCore" in t and "INCLUSIVE" in t
    assert "ot_rg_*" in RG.TCL_RELEASE.read_text()
