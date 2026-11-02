"""DIE-S81-47: tools/die_plan/place_guides.py (die-agnostic GPL register guides, the DIE-HBM-57 form) on a synthetic
geom dump: affinity through combinational cones, macro-group and anchor guides (disjoint, clear of macro halos and
fixed face registers, exact member prefixes), and the kit apply step (HBM macro_reg_guide.tcl + hooks; HBM list input)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import place_guides as PG  # noqa: E402

GR = PG._load(PG.GEOM_RULES, "geom_rules")

# 200 x 200 die, core 4.32 .. 195.68; macro A bottom-left, macro B bottom-right, ports on the north face.
# a0..a3 talk only to A (through one inverter each), b0..b1 to B and a face register f0 (north), c0 to A and B,
# r0 only to another register (no fixed endpoint).
CELLS = [
    (1, "M", "sram", 20, 20, 60, 60, "u.u_a.g_bank\\[0\\].u_m"),
    (2, "M", "sram", 140, 20, 180, 60, "u.u_b.g_bank\\[0\\].u_m"),
] + [(10 + i, "S", "DFFHQNx1", 100, 100, 101.08, 100.27, f"u.qa\\[{i}\\]$_DFF_P_") for i in range(4)] + [
    (20, "S", "DFFHQNx1", 100, 110, 101.08, 110.27, "u.qb\\[0\\]$_DFF_P_"),
    (21, "S", "DFFHQNx1", 100, 112, 101.08, 112.27, "u.qb\\[1\\]$_DFF_P_"),
    (22, "S", "DFFHQNx1", 100, 114, 101.08, 114.27, "u.qc$_DFF_P_"),
    (23, "S", "DFFHQNx1", 100, 116, 101.08, 116.27, "u.r0$_DFF_P_"),
    (30, "S", "DFFHQNx1", 100, 195, 101.08, 195.27, "u.f0$_DFF_P_"),
] + [(40 + i, "B", "INVx1", 90, 90, 90.2, 90.27, f"_{40 + i}_") for i in range(8)]


def _geom(tmp):
    rows = ["D\t0\t0\t200\t200", "R\t4.32\t4.32\t195.68\t195.68"]
    rows += [f"C\t{c[0]}\t{c[1]}\t{c[2]}\t{c[3]}\t{c[4]}\t{c[5]}\t{c[6]}\t{c[7]}" for c in CELLS]
    rows += ["P\t0\tf_o\tOUTPUT\tSIGNAL\tM3\t100\t199.9", "P\t1\tck\tINPUT\tSIGNAL\tM3\t50\t199.9"]
    nets = []
    for i in range(4):                     # qa[i] -> inv -> macro A ; macro A -> qa[i] (direct)
        nets += [f"N\tSIGNAL\ti{10 + i}\ti{40 + i}", f"N\tSIGNAL\ti{40 + i}\ti1", f"N\tSIGNAL\ti1\ti{10 + i}"]
    nets += ["N\tSIGNAL\ti2\ti20\ti21", "N\tSIGNAL\ti20\ti44", "N\tSIGNAL\ti44\ti30", "N\tSIGNAL\ti21\ti30",
             "N\tSIGNAL\ti22\ti1\ti2", "N\tSIGNAL\ti23\ti22", "N\tSIGNAL\ti30\tp0",
             "N\tCLOCK\tp1\t" + "\t".join(f"i{c[0]}c" for c in CELLS if c[1] in "SM")]
    rows += nets
    p = tmp / "geom.tsv"
    p.write_text("\n".join(rows) + "\n")
    (tmp / "face.txt").write_text("u.f0\\$_DFF_P_\tN\t100.5\t195.1\tf_o\n".replace("\\$", "$"))
    return p


def test_affinity_and_guides(tmp_path):
    D = GR.Design(str(_geom(tmp_path)))
    aff = PG.affinity(D, str(tmp_path / "face.txt"))
    r = {x["ff"]: x for x in aff["rows"]}
    assert aff["fixed"] == 1 and r["u.f0$_DFF_P_"]["fixed"]
    assert r["u.qa[0]$_DFF_P_"]["macros"] == ["u.u_a.g_bank[0].u_m"]       # through the inverter and direct
    assert r["u.qb[0]$_DFF_P_"]["fixed_ffs"] == ["u.f0$_DFF_P_"] and r["u.qb[0]$_DFF_P_"]["macros"] == ["u.u_b.g_bank[0].u_m"]
    assert sorted(r["u.qc$_DFF_P_"]["macros"]) == ["u.u_a.g_bank[0].u_m", "u.u_b.g_bank[0].u_m"]
    assert r["u.r0$_DFF_P_"]["macros"] == [] and r["u.r0$_DFF_P_"]["ff_nbrs"] == ["u.qc$_DFF_P_"]
    assert r["u.f0$_DFF_P_"]["pins"] == ["f_o"]                               # clock port never an endpoint
    mg = [("a", r"u_a\."), ("b", r"u_b\.")]
    gA = PG.build(D, aff, "macro", mg, min_ff=1, pitch=1.08)
    keys = {b["key"]: b for b in gA["boxes"]}
    assert set(keys) == {"a", "b"} and keys["a"]["ffs"] == 4 and keys["b"]["ffs"] == 2
    assert keys["a"]["prefixes"] == ["u.qa["]                                 # one exact prefix covers qa[0..3]
    assert gA["unguided"]["multi_or_ungrouped_macro"] == 1                    # qc talks to two groups
    a = keys["a"]["box_um"]
    assert PG.l1_to_box((a[0] + a[2]) / 2, (a[1] + a[3]) / 2, [20, 20, 60, 60]) < 15   # beside macro A
    assert not PG.check_overlap(gA, D, {"u.f0$_DFF_P_"})
    gB = PG.build(D, aff, "anchor", mg, min_ff=1, pitch=1.08)
    b = [x for x in gB["boxes"] if "u.qb[" in x["prefixes"]][0]["box_um"]
    yc = (b[1] + b[3]) / 2
    assert 60 < yc < 195                       # relay site between macro B (top y 60) and the face register (y 195)
    assert not PG.check_overlap(gB, D, {"u.f0$_DFF_P_"})


def test_pure_prefixes_exact():
    names = ["u.q[1]$_D", "u.q[10]$_D", "u.q[2]$_D", "u.p[1]$_D", "u.q_x"]
    assert PG.pure_prefixes(["u.q[1]$_D", "u.q[10]$_D", "u.q[2]$_D"], names) == ["u.q["]
    assert PG.pure_prefixes(["u.q[1]$_D"], names) == ["u.q[1]"]


def test_apply_kit_hbm_list_and_refusals(tmp_path):
    k = tmp_path / "kit"
    k.mkdir()
    (k / "config.mk").write_text("export CORE_AREA = 4.32 4.32 195.68 195.68\n"
                                 "export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl\n"
                                 "export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl\n")
    (k / "face_flops.tcl").write_text("# ff\n")
    (k / "face_flops_release.tcl").write_text("# rel\n")
    g = tmp_path / "register_guides.json"           # bare list = DIE-HBM-57 pslice_place_prep register_guides.json form
    g.write_text(json.dumps([dict(name="col0", prefixes=["g_c[0].u_c.og_q"], box_um=[10, 10, 30, 80]),
                             dict(name="col1", prefixes=["g_c[1].u_c.og_q"], box_um=[40, 10, 60, 80])]))
    rgb = PG.apply(str(k), str(g), "t")
    assert [x["name"] for x in rgb] == ["col0", "col1"]
    t = (k / "macro_reg_guide.tcl").read_text()
    assert "set ::ot_mrg_spec [concat {col0 {{g_c[0].u_c.og_q}} 10 10 30 80} {col1" in t and "dbRegion_create" in t
    assert (k / "face_flops.tcl").read_text().rstrip().endswith("source /work/macro_reg_guide.tcl")
    assert (k / "face_flops_release.tcl").read_text().rstrip().endswith("source /work/macro_reg_guide_release.tcl")
    try:
        PG.apply(str(k), str(g), "t")                # a guided kit is never guided twice
    except SystemExit as e:
        assert "already guided" in str(e)
    else:
        raise AssertionError("second apply accepted")
    k2 = tmp_path / "kit2"
    k2.mkdir()
    (k2 / "config.mk").write_text((k / "config.mk").read_text())
    (k2 / "face_flops.tcl").write_text("")
    (k2 / "face_flops_release.tcl").write_text("")
    g.write_text(json.dumps({"boxes": [dict(name="x", prefixes=["a."], box_um=[10, 10, 30, 30]),
                                       dict(name="y", prefixes=["a.b"], box_um=[40, 40, 50, 50])]}))
    try:
        PG.apply(str(k2), str(g))                    # nesting prefixes refused by the shared HBM validator
    except SystemExit as e:
        assert "nest" in str(e)
    else:
        raise AssertionError("nested prefixes accepted")
