"""TYPE-TEMPLATE tests (OWNER 11-19): groups need the plan layout key AND the bound RTL key, the check proves each position, the flag
marks a family, the credit writes col_inherit records the counter reads, the view clone renames one macro."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "die_plan"))
import col_inherit as CI
import type_template as TT

A, B, C, D = ("col_h9_r1__t1__cl11111111__pv00000001", "col_h9_r1__t1__cl11111111__pv00000002",
              "col_h9_r1__t1__cl11111111__pv00000003", "col_h9_r1__t1__cl11111111__pv00000004")


def ctype(name, img, mark=True, tapx=140.0):
    t = dict(module=name, outline_um=[100, 100], buses=[dict(name="ft1_i")], ft_slots=[], internal_stations=[], reset={},
             contents=[dict(inst="u0", module="m")], sources=["x.sv"], hard=False,
             hard_cores=[dict(inst="u_c0", module="ot_rom_4096x72_m8", lef="v/rom.lef", lib="v/rom_tt.lib", origin_um=[10, 20], orient="R0")],
             clock=dict(taps=[dict(name="u_c0.ck", kind="core", xy=[tapx, 20.0])], landing_contract=dict(collector_tree=dict(type=name))),
             note="x " + name, param_base_type="b", param_set={"P_u_c0_INSTANCE": '"%s"' % img})
    if mark:
        t[TT.FLAG] = True
    return t


def rtl(name, img, extra=""):
    return ("// GENERATED for %s\nmodule %s (input wire clk%s);\n  ot_rom_4096x72_m8 #(.INSTANCE(\"%s\"), .VIAMAP(\"\")) u_u_c0 (.clk(clk));\n"
            "endmodule\n" % (name, name, extra, img))


@pytest.fixture
def world(tmp_path):
    pt = {A: ctype(A, "f0.c0"), B: ctype(B, "f1.c0"), C: ctype(C, "f2.c0"), D: ctype(D, "f3.c0", mark=False)}
    plan = dict(partition_types=pt, partitions=[dict(name="p%d" % i, type=n, orient=o) for i, (n, o) in
                                                enumerate(((A, "MX"), (B, "R180"), (C, "MX"), (D, "MX")))])
    bind = tmp_path / "rtl"
    bind.mkdir()
    (bind / (A + ".sv")).write_text(rtl(A, "f0.c0"))
    (bind / (B + ".sv")).write_text(rtl(B, "f1.c0"))
    (bind / (C + ".sv")).write_text(rtl(C, "f2.c0", ", output wire rst_o_0"))      # exports a reset: another kit
    (bind / (D + ".sv")).write_text(rtl(D, "f3.c0"))
    repo = tmp_path / "src"
    (repo / "v").mkdir(parents=True)
    (repo / "v" / "rom.lef").write_text("MACRO ot_rom_4096x72_m8\nEND\n")
    (repo / "v" / "rom_tt.lib").write_text("cell (ot_rom_4096x72_m8) {}\n")
    return plan, str(bind), str(repo), tmp_path


def test_group_needs_layout_and_bound_rtl(world):
    plan, bind, _repo, _tmp = world
    gs = TT.groups(plan, bind)
    assert [(g["representative"], g["members"]) for g in gs] == [(A, [B]), (C, [])]      # D is not marked, C has another reset tree
    assert TT.member_map(plan, bind) == {B: A}
    plan["partition_types"][B]["clock"]["taps"][0]["xy"][0] = 146.0                       # another layout: no longer a member
    assert TT.member_map(plan, bind) == {}


def test_unmarked_and_missing_rtl_never_members(world):
    plan, bind, _repo, _tmp = world
    assert TT.member_map(plan, bind, globs=["col_h9_r1__*"]) == {B: A, D: A}              # --all marks by glob
    os.remove(os.path.join(bind, B + ".sv"))
    assert B not in TT.member_map(plan, bind)                                            # no bound RTL = its own kit
    assert TT.member_map(plan, None) == {}


def test_non_image_parameter_splits(world):
    plan, bind, _repo, _tmp = world
    plan["partition_types"][B]["param_set"]["P_DEPTH"] = "8"
    assert TT.member_map(plan, bind) == {}


def test_rtl_key_ignores_only_image_strings_and_own_name():
    assert TT.rtl_key(rtl(A, "x"), A) == TT.rtl_key(rtl(B, "y"), B)
    assert TT.rtl_key(rtl(A, "x"), A) != TT.rtl_key(rtl(B, "y", ", output wire rst_o_0"), B)
    assert TT.rtl_key(rtl(A, "x"), A) != TT.rtl_key(rtl(A, "x").replace(".clk(clk)", ".clk(clk2)"), A)


def test_check_every_position(world):
    plan, bind, repo, _tmp = world
    r = TT.check(plan, bind, repo)
    assert r["failed"] == [] and [p["type"] for p in r["positions"]] == [A, B, C]
    assert {p["type"]: p["orient"] for p in r["positions"]}[B] == ["R180"]
    os.remove(os.path.join(repo, "v", "rom_tt.lib"))                                     # a view file missing = not proven
    assert set(TT.check(plan, bind, repo)["failed"]) == {A, B, C}


def test_flag_marks_family(world):
    plan, bind, _repo, _tmp = world
    assert TT.flag(plan, ["col_h9_r1__*"]) == [D]
    assert TT.member_map(plan, bind) == {B: A, D: A}
    assert TT.layout_key(A, plan["partition_types"][A]) == TT.layout_key(D, plan["partition_types"][D])


def test_credit_writes_counter_rows(world):
    plan, bind, repo, tmp = world
    rom = tmp / "rom"
    rom.mkdir()
    for i in ("f0.c0", "f1.c0"):
        (rom / (i + ".viamap.hex")).write_text("0\n")
    judge = lambda path, repo=None: dict(path=str(path), sha256="s", verdict="SIGNED", gates={}, reasons=[], drc=0, tt_wns_ps=-10.0,
                                         ff_hold_wns_ps=1.0)
    tsv = tmp / "inherit_members.tsv"
    res = TT.credit(plan, bind, repo, str(rom), A, "signoff.json", str(tmp / "rec"), str(tsv), judge=judge)
    assert [(m, c) for m, _p, c in res] == [(B, True)]
    rec = json.loads(open(res[0][1]).read())
    assert rec["schema"] == CI.SCHEMA and rec["sibling"] == B and rec["representative"] == A and rec["credit"] is True
    assert rec["lec"]["verdict"] == "EQUIVALENT" and rec["differing_params"] == ["P_u_c0_INSTANCE"]
    row = tsv.read_text().strip().split("\t")
    assert row[:3] == ["s81", B, A] and row[4] == CI.sha256_file(res[0][1])
    with pytest.raises(KeyError):
        TT.credit(plan, bind, repo, str(rom), B, "signoff.json", str(tmp / "rec2"), judge=judge)       # B is a member, not a representative


def test_credit_refused_when_representative_not_signed(world):
    plan, bind, repo, tmp = world
    judge = lambda path, repo=None: dict(path=str(path), sha256="s", verdict="FAIL", gates={}, reasons=["TT -80"], drc=0, tt_wns_ps=-80.0,
                                         ff_hold_wns_ps=1.0)
    tsv = tmp / "m.tsv"
    res = TT.credit(plan, bind, repo, None, A, "signoff.json", str(tmp / "rec"), str(tsv), judge=judge)
    assert res[0][2] is False and not tsv.exists()


def test_clone_view_renames_one_macro(tmp_path):
    lef, lib = tmp_path / "a.lef", tmp_path / "a.lib"
    lef.write_text("MACRO %s\n  FOREIGN %s 0 0 ;\nEND %s\n" % (A, A, A))
    lib.write_text('library (x) {\n  cell (%s) {\n  }\n}\n' % A)
    pl, pb = TT.clone_view(A, B, str(lef), str(lib), str(tmp_path / "out"))
    assert A not in open(pl).read() and open(pl).read().count(B) == 3 and "cell (%s)" % B in open(pb).read()
    lef.write_text("MACRO other\nEND other\n")
    with pytest.raises(ValueError):
        TT.clone_view(A, B, str(lef), str(lib), str(tmp_path / "out2"))


def test_rommap_positions_images_and_lef_check(world):
    plan, bind, repo, tmp = world
    for t in plan["partition_types"].values():
        t["hard_cores"][0].update(inst="u_r1.u_c0", outline_um=[30, 60])
    plan["partitions"] = [dict(name="pA", type=A, orient="MX", origin_um=[1000, 2000]), dict(name="pB", type=B, orient="R180", origin_um=[0, 0])]
    rom = tmp / "rom"
    rom.mkdir()
    for i in ("f0.c0", "f1.c0"):
        (rom / (i + ".viamap.hex")).write_text(i + "\n")
    r = TT.rommap(plan, bind, repo, str(rom))
    assert r["errors"] == [] and r["layouts"] == [A, C] and [(p["part"], p["layout"]) for p in r["positions"]] == [("pA", A), ("pB", A)]
    a, b = r["positions"][0]["roms"][0], r["positions"][1]["roms"][0]
    assert (a["image"], b["image"]) == ("f0.c0", "f1.c0") and a["lef_sha256"] == b["lef_sha256"] and a["viamap"][0]["sha256"] != b["viamap"][0]["sha256"]
    assert a["die_xy_um"] == [1010, 2020] and a["die_orient"] == "MX"            # MX: y = 100 - 20 - 60
    assert b["die_xy_um"] == [60, 20] and b["die_orient"] == "R180"              # R180: x = 100 - 10 - 30
    os.remove(rom / "f1.c0.viamap.hex")
    assert any("no via map" in e for e in TT.rommap(plan, bind, repo, str(rom))["errors"])
    assert any(".gds" in e for e in TT.rommap(plan, bind, repo, None, gds_dir=str(tmp))["errors"])


def test_rommap_refuses_other_lef_or_site(world):
    plan, bind, repo, _tmp = world
    for t in plan["partition_types"].values():
        t["hard_cores"][0].update(inst="u_r1.u_c0", outline_um=[30, 60])
    g = lambda: TT.groups(plan, bind)
    assert TT.rommap(plan, bind, repo)["errors"] == []
    # a member whose ROM is another LEF can only reach rommap through --all style grouping errors; force it through the map itself
    import copy
    p2 = copy.deepcopy(plan)
    p2["partition_types"][B]["hard_cores"][0]["lef"] = "v/other.lef"
    orig = TT.groups
    TT.groups = lambda *a, **k: orig(plan, bind)
    try:
        assert any("LEF" in e for e in TT.rommap(p2, bind, repo)["errors"])
    finally:
        TT.groups = orig
    assert TT.die_rect([0, 0], "MY", [100, 100], [10, 20], [30, 60], "MX") == ([60, 20], "R180")
    with pytest.raises(ValueError):
        TT.die_rect([0, 0], "R90", [100, 100], [10, 20], [30, 60])


def test_records_do_not_write(world):
    plan, bind, repo, tmp = world
    judge = lambda path, repo=None: dict(path=str(path), sha256="s", verdict="SIGNED", gates={}, reasons=[], drc=0, tt_wns_ps=-1.0, ff_hold_wns_ps=1.0)
    recs = TT.records(plan, bind, repo, None, A, "x", judge=judge)
    assert [r["sibling"] for r in recs] == [B] and recs[0]["credit"] is True and not (tmp / "rec").exists()


# ---------------------------------------------------------------- S81-ROM-TEMPLATE strict rule + negative controls
SIGNED = lambda path, repo=None: dict(path=str(path), sha256="s", verdict="SIGNED", gates={}, reasons=[], drc=0, tt_wns_ps=-1.0, ff_hold_wns_ps=1.0)


@pytest.fixture
def strict(world):
    """two positions, two ROMs each, one kit dir each, real-content images with a PASS weight record"""
    plan, bind, repo, tmp = world
    pt = plan["partition_types"]
    for n in (C, D):
        del pt[n]
    plan["partitions"] = [dict(name="fW0_p1_b1", type=A), dict(name="fE0_p1_b1", type=B)]
    for n, f in ((A, "f0"), (B, "f1")):
        pt[n]["hard_cores"].append(dict(pt[n]["hard_cores"][0], inst="u_c1", origin_um=[50, 20]))
        pt[n]["param_set"] = {"P_u_c%d_INSTANCE" % i: '"%s.u.c%d"' % (f, i) for i in (0, 1)}
        (tmp / "rtl" / (n + ".sv")).write_text("module %s (input wire clk);\n" % n + "".join(
            '  ot_rom_4096x72_m8 #(.INSTANCE("%s.u.c%d"), .VIAMAP("")) u_u_c%d (.clk(clk));\n' % (f, i, i) for i in (0, 1)) + "endmodule\n")
    rom = tmp / "rom"
    rom.mkdir()
    recs = []
    for f in ("f0", "f1"):
        for i in (0, 1):
            p = rom / ("%s.u.c%d.viamap.hex" % (f, i))
            p.write_text("%s%d\n" % (f, i))
            recs.append(dict(instance="%s.u.c%d" % (f, i), viamap=p.name, viamap_sha256=CI.sha256_file(str(p))))
    man = rom / "weights.manifest.json"
    man.write_text(json.dumps(dict(schema="x", checkpoint=dict(index_sha256_seen="ab"), instances=recs)))
    (rom / "weights.verify.json").write_text(json.dumps(dict(verdict="PASS", manifest_sha256=CI.sha256_file(str(man)))))
    kits = {}
    for n, part, f in ((A, "fW0_p1_b1", "f0"), (B, "fE0_p1_b1", "f1")):
        k = tmp / "kits" / n
        (k / "rtl").mkdir(parents=True)
        (k / "config.mk").write_text("export DESIGN_NAME = %s\nexport X = /srv/a/%s/b\n" % (n, n))
        (k / "reset_tree.tcl").write_text("place u_rrl_1 100.5 20.0\n")
        (k / "kit_rtl.json").write_text(json.dumps(dict(parts=[part], tree_sha256=n, pins=3)))
        (k / "rtl" / (n + "_bound.sv")).write_text('// lane of %s\nmodule %s; rom #(.INSTANCE("%s.u.c0")) u();\nendmodule\n' % (part, n, f))
        kits[n] = str(k)

    def run(**over):
        a = dict(rom_dir=str(rom), kits=kits, weights=[str(man)])
        a.update(over)
        return TT.records(plan, bind, repo, a.pop("rom_dir"), A, "x", judge=SIGNED, rule="strict", **a)[0]
    return plan, tmp, kits, rom, man, run


def test_strict_credits_an_image_only_variant(strict):
    _plan, _tmp, _kits, _rom, _man, run = strict
    r = run()
    assert r["credit"] is True and r["credit_blockers"] == [] and r["rule"] == "strict" and r["images"] == 2 and r["kit_files_compared"] == 4


@pytest.mark.parametrize("what", ["kit_number", "kit_missing", "kit_extra", "image_swap", "image_shared", "two_frames", "no_image", "bit_flip", "same_content",
                                  "no_record", "verify_fail", "verify_other_manifest", "no_checkpoint"])
def test_strict_negative_controls(strict, what):
    plan, tmp, kits, rom, man, run = strict
    sv = tmp / "rtl" / (B + ".sv")
    over = {}
    if what == "kit_number":                                                  # one reset relay 0.1 um away in the generated kit
        (tmp / "kits" / B / "reset_tree.tcl").write_text("place u_rrl_1 100.6 20.0\n")
    elif what == "kit_missing":
        over = dict(kits={A: kits[A]})
    elif what == "kit_extra":
        (tmp / "kits" / B / "extra_hook.tcl").write_text("\n")
    elif what == "image_swap":                                                # c0 carries c1's weights and the reverse: same rtl key
        sv.write_text(sv.read_text().replace("f1.u.c0", "@").replace("f1.u.c1", "f1.u.c0").replace("@", "f1.u.c1"))
    elif what == "image_shared":
        sv.write_text(sv.read_text().replace("f1.u.c1", "f0.u.c1"))
    elif what == "two_frames":
        sv.write_text(sv.read_text().replace("f1.u.c1", "f2.u.c1"))
    elif what == "no_image":
        (rom / "f1.u.c1.viamap.hex").unlink()
    elif what == "bit_flip":
        (rom / "f1.u.c1.viamap.hex").write_text("f10\n")
    elif what == "same_content":                                              # a member with the representative's weights is not another image
        m = json.loads(man.read_text())
        for i in (0, 1):
            (rom / ("f1.u.c%d.viamap.hex" % i)).write_text("f0%d\n" % i)
            m["instances"][2 + i]["viamap_sha256"] = m["instances"][i]["viamap_sha256"]
        man.write_text(json.dumps(m))
        (rom / "weights.verify.json").write_text(json.dumps(dict(verdict="PASS", manifest_sha256=CI.sha256_file(str(man)))))
    elif what == "no_record":
        over = dict(weights=[])
    elif what == "verify_fail":
        (rom / "weights.verify.json").write_text(json.dumps(dict(verdict="FAIL", manifest_sha256=CI.sha256_file(str(man)))))
    elif what == "verify_other_manifest":
        man.write_text(man.read_text() + "\n")
    elif what == "no_checkpoint":
        m = json.loads(man.read_text())
        m["checkpoint"] = {}
        man.write_text(json.dumps(m))
        (rom / "weights.verify.json").write_text(json.dumps(dict(verdict="PASS", manifest_sha256=CI.sha256_file(str(man)))))
    r = run(**over)
    assert r["credit"] is False, what
    word = dict(kit_number="kit file(s) differ", kit_missing="no generated kit", kit_extra="kit file(s) differ", image_swap="permuted",
                image_shared="named by another", two_frames="more than one frame", no_image="no via map", bit_flip="not in a PASS weight record",
                same_content="not a different image", no_record="not in a PASS", verify_fail="not PASS", verify_other_manifest="not PASS",
                no_checkpoint="no checkpoint")[what]
    assert any(word in b for b in r["credit_blockers"]), (what, r["credit_blockers"])


def test_strict_image_string_on_soft_logic_is_not_masked():
    """negative control of the by-construction LEC: an image string that reaches a module which is not a placed hard core is logic"""
    a = 'module X (input wire clk);\n  soft_mod #(.INSTANCE("f0.c0")) u_s (.clk(clk));\nendmodule\n'
    assert TT.rtl_key(a, "X") == TT.rtl_key(a.replace("f0", "f1"), "X")                                       # the 11-19 key is blind to it
    assert TT.rtl_key(a, "X", {"ot_rom"}) != TT.rtl_key(a.replace("f0", "f1"), "X", {"ot_rom"})
    r = a.replace("soft_mod", "ot_rom")
    assert TT.rtl_key(r, "X", {"ot_rom"}) == TT.rtl_key(r.replace("f0", "f1"), "X", {"ot_rom"})
    assert TT.rtl_key(r, "X", {"ot_rom"}) != TT.rtl_key(r.replace("(clk)", "(clk2)"), "X", {"ot_rom"})


def test_kit_norm_keeps_numbers():
    n = lambda s, code=False: TT.kit_norm(s, A, ["fW0_p1_b1"], {"f0.c0"}, code)
    assert n("set x 1.0  # // keep") != n("set x 1.1  # // keep")
    assert n('"tree_sha256": "a"') == n('"tree_sha256": "b"') and n('"pins": 3') != n('"pins": 4')
    assert n("fW0_p1_b11") == "fW0_p1_b11" and n("fW0_p1_b1") == "@P" and n("// c", True) == ""
