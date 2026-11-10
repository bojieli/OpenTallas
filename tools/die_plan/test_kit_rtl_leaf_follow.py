"""KW-FIX-35-US 11-08: class UNINDEXED-SRC-STALE (S81-TYPES-9-LEC 09:50).

kit-rtl closed the leaf RTL in the as-built manifest's own FROZEN base tree, so a leaf fix in the wave source never
reached a relaunched kit (S81 J2 xs_ctl / J3 xs4 + rstopt_xo failed LEC again).  Leaf sources now follow the wave
source (bind.LeafFollow); a leaf that differs and cannot follow fails closed; hardened child views stay in the bind
tree.  The MUTANT test plants a stale leaf in the as-built tree: without the follow the kit takes it (the class), with
it the kit takes the wave file, and a stale leaf with another module set refuses.
python3 -m pytest tools/die_plan/test_kit_rtl_leaf_follow.py
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
needs_yosys = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
STALE = "kw35us_stale_marker"


def w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


MOD = "module m_a (input wire a, output wire y);\n  assign y = a;\nendmodule\n"


def test_classify_follow_same_mismatch_view_frozen(tmp_path):
    base, src = tmp_path / "frozen", tmp_path / "wave"
    old = w(base / "rtl" / "x" / "a.sv", MOD + f"// {STALE}\n")
    new = w(src / "rtl" / "x" / "a.sv", MOD)
    same = w(base / "rtl" / "b.sv", "module m_b; endmodule\n")
    w(src / "rtl" / "b.sv", "module m_b; endmodule\n")
    bad = w(base / "rtl" / "c.sv", "module m_c; endmodule\n")
    w(src / "rtl" / "c.sv", "module m_c2; endmodule\n")             # m_c gone from the wave file: cannot follow
    sup = w(base / "rtl" / "d.sv", "module m_d; endmodule\n")
    w(src / "rtl" / "d.sv", "module m_d; endmodule\nmodule m_d_helper; endmodule\n")
    view = w(base / "physical" / "m_v" / "m_v_bb.v", "module m_v; endmodule\n")
    w(base / "physical" / "m_v" / "m_v.lef", "MACRO m_v\n")
    w(src / "physical" / "m_v" / "m_v_bb.v", "module m_v (input wire z); endmodule\n")
    only = w(base / "rtl" / "only.sv", "module m_o; endmodule\n")
    lane = w(tmp_path / "lane_wt" / "rtl" / "x" / "a.sv", MOD + "// lane copy\n")   # absolute pin in an old lane tree
    gen = w(tmp_path / "bind_out" / "rtl" / "x" / "a.sv", MOD + "// bind output\n")
    lf = bind.LeafFollow(base, src, exclude=[tmp_path / "bind_out"])
    assert lf.active()
    assert lf.classify(str(old))[:2] == ("followed", str(new.resolve()))
    assert lf.classify(str(same))[0] == "same"
    assert lf.classify(str(bad))[0] == "mismatch"
    assert lf.classify(str(sup))[0] == "followed"                     # an added helper module still follows
    assert lf.classify(str(view))[:2] == ("view", str(view))          # signed child view stays in the bind tree
    assert lf.classify(str(only))[:2] == ("frozen", str(only))
    assert lf.classify(str(lane))[:2] == ("followed", str(new.resolve()))
    assert lf.classify(str(gen))[:2] == ("src", str(gen))
    assert lf.map_list([str(old), str(lane)]) == [str(new.resolve())]
    lf.check("t", [str(new), str(view), str(only)])                    # followed / view / frozen: no error
    with pytest.raises(bind.BindError, match="UNINDEXED-SRC-STALE"):
        lf.check("t", [str(bad)])
    rec = lf.record()
    assert {r["was"] for r in rec["followed"]} == {str(old), str(lane), str(sup)} and rec["same"] == 1
    # inactive when the as-built base is inside the wave source (repo-relative examples): nothing changes
    lf2 = bind.LeafFollow(src, src)
    assert not lf2.active() and lf2.classify(str(new))[0] == "src"


def test_library_profile_replacement_is_kept(tmp_path):
    base, src = tmp_path / "frozen", tmp_path / "wave"
    rep = w(base / "rtl" / "a.sv", MOD + "// candidate\n")
    w(src / "rtl" / "a.sv", MOD)
    assert bind.LeafFollow(base, src, keep=[rep]).classify(str(rep))[0] == "pinned"


def frozen_plan(tmp_path, leaves_text):
    """bind_tiny with its as-built base copied to a FROZEN tree whose leaves.sv is `leaves_text`"""
    fz = tmp_path / "frozen"
    fz.mkdir()
    for f in EX.iterdir():
        if f.is_file():
            shutil.copy(f, fz / f.name)
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    p["asbuilt"]["base"] = str(fz)
    plan = tmp_path / "die_plan_lanes.json"
    plan.write_text(json.dumps(p))
    out = tmp_path / "o"
    for c in ("elab", "bind"):
        assert bind.main([c, str(plan), "--out", str(out), "--mem", "4"]) == 0
    (fz / "leaves.sv").write_text(leaves_text)          # the mutant: the frozen tree's leaf is stale vs the wave
    top = next((out / "rtl").glob("*_bound_top.sv")).read_text()
    inst = re.findall(r"^\s*\w+ #\(.*?\) (\w+) \(", top, re.M)[0]
    return plan, out, inst, fz


def kit(plan, out, inst, kd, src):
    old = bind.LEAF_SRC
    bind.LEAF_SRC = str(src)
    try:
        return bind.main(["kit-rtl", str(plan), "--out", str(out), "--type", "ta", "--instance", inst, "--kit", str(kd)])
    finally:
        bind.LEAF_SRC = old


def flist(kd):
    return [str(Path(f).resolve()) for f in (Path(kd) / "kit_rtl.f").read_text().split()]


@needs_yosys
def test_mutant_stale_leaf_follows_wave_src(tmp_path):
    good = (EX / "leaves.sv").read_text()
    plan, out, inst, fz = frozen_plan(tmp_path, good.replace("o <= i + ID[7:0];", f"o <= i - ID[7:0]; // {STALE}"))
    wave = tmp_path / "wave"
    w(wave / "leaves.sv", good)
    stale = str((fz / "leaves.sv").resolve())
    # the class: kit-rtl following the frozen tree itself (= old behaviour) builds the stale leaf
    assert kit(plan, out, inst, tmp_path / "k0", fz) == 0
    assert stale in flist(tmp_path / "k0")
    # the fix: the leaf resolves to the wave source
    assert kit(plan, out, inst, tmp_path / "k1", wave) == 0
    fl = flist(tmp_path / "k1")
    assert stale not in fl and str((wave / "leaves.sv").resolve()) in fl
    assert not any(STALE in Path(f).read_text() for f in fl)
    man = json.loads((tmp_path / "k1" / "kit_rtl.json").read_text())
    rows = man["leaf_follow"]["followed"]
    assert [r["file"] for r in rows] == ["leaves.sv"] and rows[0]["was"] == stale


@needs_yosys
def test_mutant_stale_leaf_lost_module_fails_closed(tmp_path):
    good = (EX / "leaves.sv").read_text()
    plan, out, inst, fz = frozen_plan(tmp_path, good + f"// {STALE}\n")
    wave = tmp_path / "wave"
    wave_text = re.sub(r"module lf_b_nid .*?endmodule\n", "", good, flags=re.S)
    assert "lf_b_nid" not in wave_text
    w(wave / "leaves.sv", wave_text)                    # the wave file lacks a module of the stale one: cannot follow
    assert kit(plan, out, inst, tmp_path / "k2", wave) != 0
    assert not (tmp_path / "k2" / "kit_rtl.f").exists()
