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
