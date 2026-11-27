"""kit_flow_refresh: a kit's verbatim copy of an older main flow script is replaced by the rt version; generated files never."""
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_flow_refresh as K


def setup(tmp):
    rt = Path(tmp) / "rt" / "aaaaaaaaaaaa"
    (rt / "tools/die_plan").mkdir(parents=True)
    (rt / "physical/common_flow").mkdir(parents=True)
    old, new = b"puts old\n", b"puts fixed\n"
    (rt / "tools/die_plan/vclk_measured_hold.tcl").write_bytes(new)
    (rt / "physical/common_flow/grt183_make.sh").write_bytes(b"echo same\n")
    idx = {"blobs": {"tools/die_plan/vclk_measured_hold.tcl": sorted({K.blob_id(old), K.blob_id(new)}),
                     "physical/common_flow/grt183_make.sh": [K.blob_id(b"echo same\n")],
                     "tools/die_plan/gen_lint.tcl": [K.blob_id(b"stock\n")]}}
    (rt / "tools/.flow_blobs.json").write_text(json.dumps(idx))
    Path(str(rt) + ".manifest.json").write_text(json.dumps({"sha": "a" * 40}))
    kit = Path(tmp) / "kit"
    kit.mkdir()
    (kit / "vclk_measured_hold.tcl").write_bytes(old)
    (kit / "grt183_make.sh").write_bytes(b"echo same\n")
    (kit / "gen_lint.tcl").write_bytes(b"generated for this kit\n")
    (kit / "run_kit.sh").write_bytes(b"#!/bin/bash\n")
    return rt, kit


def test_replaces_only_verbatim_old_copies():
    rt, kit = setup(tempfile.mkdtemp())
    assert K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)]) == 0
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts fixed\n"
    assert (kit / "gen_lint.tcl").read_bytes() == b"generated for this kit\n"
    rec = json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])
    assert rec["sha"] == "a" * 40 and rec["stage"] == "route" and [r["file"] for r in rec["replaced"]] == ["vclk_measured_hold.tcl"]
    K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)])          # idempotent: nothing more to replace
    assert json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])["replaced"] == []


def test_no_index_and_opt_out_touch_nothing(monkeypatch):
    rt, kit = setup(tempfile.mkdtemp())
    (rt / "tools/.flow_blobs.json").unlink()
    K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)])
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts old\n"
    (rt / "tools/.flow_blobs.json").write_text(json.dumps({"blobs": {"tools/die_plan/vclk_measured_hold.tcl": [K.blob_id(b"puts old\n")]}}))
    monkeypatch.setenv("OT_FLOW_REFRESH", "0")
    K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)])
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts old\n"


def test_blob_id_matches_git():
    import subprocess
    d = tempfile.mkdtemp()
    p = Path(d) / "f"
    p.write_bytes(b"hello\n")
    assert K.blob_id(b"hello\n") == subprocess.run(["git", "hash-object", str(p)], capture_output=True, text=True).stdout.strip()


def test_bundle_layout_from_signoff_chain(capsys):
    """FABLE-FLOW-1000 A: inside the sealed job the chain runs from the admission bundle: refresher + index + scripts are there"""
    import shutil, subprocess
    tmp = Path(tempfile.mkdtemp())
    rt, kit = setup(tmp)
    b = tmp / "bundle"
    (b / "die_plan/__flow__/common_flow").mkdir(parents=True)
    shutil.copy(rt / "tools/die_plan/vclk_measured_hold.tcl", b / "die_plan/vclk_measured_hold.tcl")
    shutil.copy(rt / "tools/.flow_blobs.json", b / "die_plan/__flow__/flow_blobs.json")
    shutil.copy(Path(K.__file__), b / "die_plan/__flow__/kit_flow_refresh.py")
    import signoff_chain as SC
    SC.flow_refresh(kit, "route", script="/nonexistent", bundle=b)
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts fixed\n"
    assert json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])["stage"] == "route"


def test_skip_is_loud(capsys):
    import signoff_chain as SC
    tmp = Path(tempfile.mkdtemp())
    SC.flow_refresh(tmp, "route", script="/nonexistent", bundle=tmp)
    assert "KIT_FLOW_REFRESH SKIPPED" in capsys.readouterr().out


def die_setup(tmp):
    """TOOLS-DECOUPLE-2: a die tree with an OLD gate copy, rt with the fixed one, a kit that took the die tree's copy"""
    rt = Path(tmp) / "rt" / "bbbbbbbbbbbb"
    (rt / "tools/autopilot").mkdir(parents=True)
    (rt / "tools/die_plan").mkdir(parents=True)
    (rt / "tools/autopilot/gp_noconverge.py").write_bytes(b"fixed gate\n")
    (rt / "tools/die_plan/gp_noconverge_gate.tcl").write_bytes(b"same tcl\n")
    (rt / "tools/die_plan/only_rt.tcl").write_bytes(b"rt only\n")
    Path(str(rt) + ".manifest.json").write_text(json.dumps({"sha": "b" * 40}))
    die = Path(tmp) / "src_die"
    (die / "tools/autopilot").mkdir(parents=True)
    (die / "tools/die_plan").mkdir(parents=True)
    (die / "tools/autopilot/gp_noconverge.py").write_bytes(b"old gate\n")
    (die / "tools/die_plan/gp_noconverge_gate.tcl").write_bytes(b"same tcl\n")
    (die / "tools/die_plan/die_only.tcl").write_bytes(b"only the die has this\n")
    kit = Path(tmp) / "kit"
    kit.mkdir()
    (kit / "gp_noconverge.py").write_bytes(b"old gate\n")
    (kit / "gp_noconverge_gate.tcl").write_bytes(b"same tcl\n")
    (kit / "die_only.tcl").write_bytes(b"only the die has this\n")
    (kit / "config.mk").write_bytes(b"generated\n")
    (kit / "gen_made.tcl").write_bytes(b"generated, in neither tree\n")
    return rt, die, kit


def test_die_tree_copy_replaced_by_rt_and_tools_rev_written():
    rt, die, kit = die_setup(tempfile.mkdtemp())
    assert K.main(["--kit", str(kit), "--stage", "gen", "--rt", str(rt), "--die-src", str(die)]) == 0
    assert (kit / "gp_noconverge.py").read_bytes() == (rt / "tools/autopilot/gp_noconverge.py").read_bytes()
    assert (kit / "gen_made.tcl").read_bytes() == b"generated, in neither tree\n"
    assert (kit / "die_only.tcl").read_bytes() == b"only the die has this\n"
    rev = json.loads((kit / "tools_rev.json").read_text())
    assert rev["tools_sha"] == "b" * 40 and rev["stage"] == "gen"
    assert rev["die_tree_copies_replaced"] == ["gp_noconverge.py"]
    assert rev["rt_files"] == {"gp_noconverge.py": "tools/autopilot/gp_noconverge.py", "gp_noconverge_gate.tcl": "tools/die_plan/gp_noconverge_gate.tcl"}
    assert rev["die_tree_only"] == ["die_only.tcl"]
    K.main(["--kit", str(kit), "--stage", "place", "--rt", str(rt), "--die-src", str(die)])       # idempotent
    assert json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])["replaced"] == []


def test_composed_launch_tree_fill_counts_as_die_only():
    """--rt may be the composed launch tree: a file listed in .rt_launch_filled is the die tree's, not rt's"""
    tmp = tempfile.mkdtemp()
    rt, die, kit = die_setup(tmp)
    (rt / "tools/die_plan/die_only.tcl").write_bytes(b"only the die has this\n")      # hardlinked in by the fill step
    (rt / ".rt_launch_filled").write_text("tools/die_plan/die_only.tcl\n")
    K.main(["--kit", str(kit), "--stage", "gen", "--rt", str(rt), "--die-src", str(die)])
    rev = json.loads((kit / "tools_rev.json").read_text())
    assert rev["die_tree_only"] == ["die_only.tcl"] and "die_only.tcl" not in rev["rt_files"]


def test_without_die_src_nothing_new_is_written():
    rt, die, kit = die_setup(tempfile.mkdtemp())
    K.main(["--kit", str(kit), "--stage", "gen", "--rt", str(rt)])
    assert not (kit / "tools_rev.json").exists() and (kit / "gp_noconverge.py").read_bytes() == b"old gate\n"


def test_main_copy_keeps_kit_original_source_lines(tmp_path):
    """CLOCK-TAPS-COPY-TRAP 11-25: main's clock_taps.tcl over a kit file must keep gen's `source /work/...` lines (CTS-0114 on every serdes kit)"""
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "vpw_bank_clock.tcl").write_text("# bank\n")
    (kit / "landing_exports.tcl").write_text("# land\n")
    p = kit / "clock_taps.tcl"
    p.write_bytes(b'if {![file exists /work/vpw_bank_clock.tcl]} {error "x"}\nsource /work/vpw_bank_clock.tcl\nputs main_old\nputs more\nputs more2\nsource /work/landing_exports.tcl\n')
    K._put(str(p), b"puts main_new\nputs more\n")
    t = p.read_text()
    assert t.startswith('if {![file exists /work/vpw_bank_clock.tcl]} {error "x"}\nsource /work/vpw_bank_clock.tcl\nputs main_new')
    assert t.rstrip().endswith("source /work/landing_exports.tcl")
    assert "main_old" not in t
    K._put(str(p), t.encode())                      # idempotent: nothing duplicated
    assert p.read_text() == t


def test_vpw_required_source_survives_before_placement_generates_it(tmp_path):
    p = tmp_path / "clock_taps.tcl"
    prefix = (b'if {![file exists /work/vpw_bank_clock.tcl]} {error "missing placement clock record"}\n'
              b"source /work/vpw_bank_clock.tcl\n")
    p.write_bytes(prefix + b"puts old\nputs old clock\n")
    assert not (tmp_path / "vpw_bank_clock.tcl").exists()
    K._put(str(p), b"puts new clock\n")
    assert p.read_bytes() == prefix + b"puts new clock\n"


def test_source_line_kept_only_when_the_file_is_in_the_kit(tmp_path):
    kit = tmp_path / "k"
    kit.mkdir()
    p = kit / "a.tcl"
    p.write_bytes(b"source /work/gone.tcl\nputs a\n")
    K._put(str(p), b"puts b\n")
    assert p.read_bytes() == b"puts b\n"


def test_authored_polarity_table_blocks_incompatible_hook_downgrade(tmp_path):
    rt, kit = setup(tmp_path)
    sidecar = kit / "ft_polarity_local_sites.tsv"
    sidecar.write_text("0\t8.64\t4.59\n")
    hook = kit / "ft_polarity_local.tcl"
    compatible = b"proc fpl_load_exact_sites {path} {}\n"
    hook.write_bytes(compatible)
    older = rt / "tools/die_plan/ft_polarity_local.tcl"
    older.write_text("puts legacy\n")
    index = rt / "tools/.flow_blobs.json"
    data = json.loads(index.read_text())
    data["blobs"]["tools/die_plan/ft_polarity_local.tcl"] = [K.blob_id(compatible)]
    index.write_text(json.dumps(data))
    args = ["--kit", str(kit), "--stage", "place", "--rt", str(rt)]
    assert K.main(args) == K.PARTIAL_RC
    assert hook.read_bytes() == compatible
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts old\n"
    older.write_bytes(compatible + b"# refreshed hook\n")
    assert K.main(args) == 0
    assert hook.read_bytes() == older.read_bytes()
    assert sidecar.read_text() == "0\t8.64\t4.59\n"
