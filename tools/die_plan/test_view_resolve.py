"""DIE-KV-60/adp 11-01: plan macro views resolve from a sparse / pruned source checkout (KIT-WAVE kv3_sys_SD class).

KIT-WAVE gen ran `gen.py phys` in a sparse source checkout without results/, so the repo-relative SerDes view
results/kv_serdes_pg_event33/<m>/<m>.lef raised FileNotFoundError.  cores.resolve now reads such a view from the
checkout's git store (HEAD) and relocates a stale absolute path; gen_phys and fully_fixed_macros use it."""
import json
import subprocess
from pathlib import Path

import pytest

import cores
import gen_phys as G

LEF = "VERSION 5.8 ;\nMACRO m\n  SIZE 8.64 BY 8.64 ;\n  PIN VDD\n    USE POWER ;\n    PORT\n      LAYER M6 ;\n" \
      "      RECT 0 0 8.64 0.2 ;\n    END\n  END VDD\n  PIN VSS\n    USE GROUND ;\n    PORT\n      LAYER M6 ;\n" \
      "      RECT 0 1 8.64 1.2 ;\n    END\n  END VSS\nEND m\nEND LIBRARY\n"


def _git(d, *a):
    subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True)


@pytest.fixture
def sparse(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_VIEW_CACHE", str(tmp_path / "cache"))
    src = tmp_path / "src"
    v = src / "results/ev33/m"
    v.mkdir(parents=True)
    (v / "m.lef").write_text(LEF)
    (v / "m_tt.lib").write_text("library(m_tt) {}\n")
    (v / "m_ff.lib").write_text("library(m_ff) {}\n")
    (src / "tools").mkdir()
    (src / "tools/x.txt").write_text("x\n")
    _git(src, "init", "-q")
    _git(src, "-c", "user.email=t@t", "-c", "user.name=t", "add", "results", "tools")
    _git(src, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v")
    _git(src, "sparse-checkout", "set", "--no-cone", "/tools/")
    assert not (src / "results/ev33/m/m.lef").exists()      # the KIT-WAVE source state
    return src


def test_repo_relative_view_from_git_store(sparse):
    f = cores.resolve("results/ev33/m/m.lef", sparse)
    assert f.is_file() and f.read_text() == LEF
    assert (f.parent / "m_ff.lib").is_file()                # corner siblings come with the view directory
    assert not (sparse / "results").exists()                # the sparse working tree is not touched
    assert cores.resolve("results/ev33/m/m.lef", sparse) == f   # content-addressed cache reused


def test_existing_cache_tree_dir_without_view_dir(sparse, tmp_path):
    tree = subprocess.run(["git", "-C", str(sparse), "rev-parse", "HEAD:results/ev33/m"], capture_output=True,
                          text=True, check=True).stdout.strip()
    (tmp_path / "cache" / f"{tree}.l1").mkdir(parents=True)  # e.g. an older cache layout / a concurrent writer
    f = cores.resolve("results/ev33/m/m.lef", sparse)
    assert f.is_file() and f.parent.name == "m"


def test_stale_absolute_path_relocates(sparse):
    f = cores.resolve("/srv/pruned-worktree/results/ev33/m/m_tt.lib", sparse)
    assert f.is_file() and "m_tt" in f.read_text()


def test_existing_and_unknown_paths_unchanged(sparse, tmp_path):
    assert cores.resolve("tools/x.txt", sparse) == sparse / "tools/x.txt"
    assert cores.resolve("results/ev33/m/none.lef", sparse) == sparse / "results/ev33/m/none.lef"
    assert cores.resolve("/abs/none/x.lef", sparse) == Path("/abs/none/x.lef")
    assert cores.resolve("results/a.lef", tmp_path / "nogit") == tmp_path / "nogit/results/a.lef"


def test_gen_phys_phy_pg_layers_read_through_resolver(sparse, tmp_path):
    # phy_pg_pdn / write_type_kit / bump_pin_sites / fully_fixed_macros all read views via cores.resolve
    assert G._macro_pg_layers(G._CR.resolve("results/ev33/m/m.lef", sparse)) == "M6 M7"
    import fully_fixed_macros as FFM
    t = dict(fully_fixed_macros=True, contents=[dict(inst="u_m", lef="results/ev33/m/m.lef", outline_um=[8.64, 8.64])])
    lines = FFM.install(t, tmp_path, [("u_m", "m", "results/ev33/m/m.lef", "results/ev33/m/m_tt.lib", 0, 0, "R0")],
                        [0, 0, 100, 100], sparse)
    assert lines == ['export PRE_MACRO_PLACE_TCL = /work/fully_fixed_macros.tcl']
    assert json.loads((tmp_path / 'fully_fixed_macros.json').read_text())['macros'][0]['outline_um'] == [8.64, 8.64]


def test_serdes_specializer_finds_repo_relative_view_in_sparse_source(tmp_path, monkeypatch):
    # bind.py kit-rtl -> specialize_serdes_phy.specialize_plan(kit, type, source_root): same class (06:35 / 06:57)
    import specialize_serdes_phy as S
    monkeypatch.setenv("OT_VIEW_CACHE", str(tmp_path / "cache"))
    src, master = tmp_path / "src", S.LOGICAL + "_w522"
    v = src / "results/ev33" / master
    v.mkdir(parents=True)
    hdr = (" input wire clk, rst_n, output wire tx_up, input wire tx_v,\n input wire [{w}-1:0] tx_flit, output wire rx_v,\n"
           " output wire [{w}-1:0] rx_flit);\nendmodule\n")
    (v / f"{master}_bb.v").write_text(f"(* blackbox *)\nmodule {master} (\n" + hdr.format(w="522"))
    for s in (".lef", "_tt.lib", "_ff.lib"):
        (v / (master + s)).write_text("view\n")
    (src / "tools").mkdir()
    (src / "tools/x.txt").write_text("x\n")
    _git(src, "init", "-q")
    _git(src, "-c", "user.email=t@t", "-c", "user.name=t", "add", "results", "tools")
    _git(src, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v")
    _git(src, "sparse-checkout", "set", "--no-cone", "/tools/")
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "bound.sv").write_text(f"module bound;\n {S.WRAPPER} #(.W(522)) u_core ( );\nendmodule\n")
    (kit / "raw_bb.v").write_text(f"(* blackbox *)\nmodule {S.LOGICAL} #(parameter integer W=522) (\n" + hdr.format(w="W"))
    (kit / "kit_rtl.json").write_text(json.dumps(dict(bound_module="bound", hard_macros={},
                                                      files=[str(kit / "bound.sv"), str(kit / "raw_bb.v")])))
    lef = f"results/ev33/{master}/{master}.lef"
    plan = dict(contents=[dict(physical_master=master, physical_inst="u_bound.u_core.u_phy.g_native.u_macro", lef=lef)])
    assert not (src / lef).exists()
    rec = S.specialize_plan(kit, plan, src)
    assert rec["physical_master"] == master and (kit / "physical_specialization").is_dir()
    assert Path(json.loads((kit / "kit_rtl.json").read_text())["hard_macros"][master]["lef"]).is_file()


@pytest.fixture
def sparse_links(tmp_path, monkeypatch):
    """KW-FIX-16 11-05 (DIE-HEAD-70 hd_tile gen phys 'VDD has no PG pin geometry'): view dirs whose LEF/Liberty are
    git symlinks into a shared master dir; the sparse checkout carries neither."""
    monkeypatch.setenv("OT_VIEW_CACHE", str(tmp_path / "cache"))
    src = tmp_path / "src"
    m, v = src / "results/ev33/master", src / "results/ev33/m"
    m.mkdir(parents=True)
    v.mkdir(parents=True)
    (m / "m.lef").write_text(LEF)
    (m / "m_tt.lib").write_text("library(m_tt) {}\n")
    (v / "m.lef").symlink_to("../master/m.lef")
    (v / "hop.lib").symlink_to("../master/m_tt.lib")
    (v / "m_tt.lib").symlink_to("hop.lib")                # chain: link -> link -> file
    (v / "gone.lib").symlink_to("../master/none.lib")     # dangling
    (v / "out.lef").symlink_to("../../../../outside.lef") # leaves the repository
    (src / "tools").mkdir()
    (src / "tools/x.txt").write_text("x\n")
    _git(src, "init", "-q")
    _git(src, "-c", "user.email=t@t", "-c", "user.name=t", "add", "results", "tools")
    _git(src, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v")
    _git(src, "sparse-checkout", "set", "--no-cone", "/tools/")
    assert not (src / "results").exists()
    return src


def test_symlink_blob_view_materialises_target_bytes(sparse_links):
    f = cores.resolve("results/ev33/m/m.lef", sparse_links)
    assert f.is_file() and not f.is_symlink() and f.read_text() == LEF   # was the 15-byte link text '../master/m.lef'
    assert (f.parent / "m_tt.lib").read_text() == "library(m_tt) {}\n"  # chain followed
    assert not (f.parent / "gone.lib").exists() and not (f.parent / "out.lef").exists()   # no stubs
    assert G._macro_pg_layers(f) == "M6 M7"                               # the hd_tile PG read works


def test_symlink_blob_cache_stub_from_old_layout_not_reused(sparse_links, tmp_path):
    tree = subprocess.run(["git", "-C", str(sparse_links), "rev-parse", "HEAD:results/ev33/m"], capture_output=True,
                          text=True, check=True).stdout.strip()
    old = tmp_path / "cache" / tree / "m"
    old.mkdir(parents=True)
    (old / "m.lef").write_text("../master/m.lef")         # what the pre-fix resolver cached
    f = cores.resolve("results/ev33/m/m.lef", sparse_links)
    assert f.read_text() == LEF and f.parent != old


def test_symlink_target_present_on_disk_is_read(sparse_links):
    _git(sparse_links, "sparse-checkout", "set", "--no-cone", "/tools/", "/results/ev33/master/")
    assert (sparse_links / "results/ev33/master/m.lef").is_file() and not (sparse_links / "results/ev33/m").exists()
    f = cores.resolve("results/ev33/m/m.lef", sparse_links)
    assert f.read_text() == LEF
