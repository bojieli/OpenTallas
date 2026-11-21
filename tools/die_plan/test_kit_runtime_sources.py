"""WAVE-FLOW-R2 11-17 (COORD): the class "a kit reads a repo file at runtime that a sparse lane clone does not have" (global_route.tcl line 191 read
physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl from /src: 6 svc cores failed GRT).  Every literal /src/<path> that the common flow sources or reads is
checked against what a kit / sparse clone carries."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import kit_common_files as K  # noqa: E402

SCAN_DIRS = ("physical/common_flow", "tools/die_plan")
READ_RE = re.compile(r"(?:^|[;{\[\s])(source|read_sdc|read_verilog|read_lef|read_liberty|read_db|read_def|read)\s+(?:-\w+\s+)*[{\"]?(/src/[^\s\"}\];$]+)")
# paths a sparse lane clone has: tools/ and physical/common_flow/ (the clone's sparse set); everything else must be carried by the kit or guarded
CARRIED_PREFIXES = ("tools/", "physical/common_flow/")
# runtime dependencies outside that set that are accepted on purpose: path -> why
ALLOW = {
    "physical/qwen_die_masters/out_flop_release.tcl": "out_flop_release_pbp.tcl is used by the qwen die kits, whose tree carries physical/qwen_die_masters",
}


def runtime_sources():
    """{repo path: [(file, line, guarded)]} for every literal /src/<path> a common-flow script sources or reads"""
    out = {}
    for d in SCAN_DIRS:
        for p in sorted((REPO / d).glob("*.tcl")) + sorted((REPO / d).glob("*.sdc")):
            for i, ln in enumerate(p.read_text(errors="replace").splitlines(), 1):
                if ln.lstrip().startswith("#"):
                    continue
                for m in READ_RE.finditer(ln):
                    if "$" in m.group(2):
                        continue
                    guarded = any(t in ln for t in ("file exists", "file isfile", "catch"))
                    out.setdefault(m.group(2)[len("/src/"):], []).append((f"{d}/{p.name}", i, guarded))
    return out


def test_every_runtime_source_of_the_common_flow_is_carried_guarded_or_allowed():
    carried = {rel for rel in K.FILES.values()}
    bad = []
    for rel, uses in runtime_sources().items():
        if rel.startswith(CARRIED_PREFIXES) or rel in carried or rel in ALLOW:
            continue
        if all(g for _, _, g in uses):
            continue
        bad.append(f"{rel} (from {uses[0][0]}:{uses[0][1]})")
    assert not bad, ("a common-flow script reads a repo file that a sparse lane clone does not carry: add it to tools/die_plan/kit_common_files.py FILES "
                     "(and source the kit copy), guard it with `file exists`, or allow it here with a reason: " + "; ".join(bad))


# tools/ref_tile/ref_tile.py writes tcl into every ref_tile kit: its string-literal `source /src/<path>` lines get the same check (S81-SVC-SPLIT: it wrote the stn_pin_keepout source)
REF_TILE_ALLOW = {
    "physical/dsrom_window_source/leaf_inhold_release.tcl": "dsrom window kits: their tree carries physical/dsrom_window_source (spec-selected hook)",
    "physical/dsrom_window_source/": "dsrom window kits (hook name from the spec)",
    "physical/hbm_w2_rb_station_20261006/forwarded_subtree.tcl": "forwarded-subtree station kits (hbm): their tree carries physical/hbm_w2_rb_station_20261006",
}
REF_RE = re.compile(r"(?:source|read_sdc|read_verilog|read_lef|read_liberty|read_db|read_def|read)\s+(?:-\w+\s+)*[{\\\"]*(/src/[A-Za-z0-9_./-]+)")


def ref_tile_sources():
    out = {}
    p = REPO / "tools/ref_tile/ref_tile.py"
    for i, ln in enumerate(p.read_text(errors="replace").splitlines(), 1):
        if ln.lstrip().startswith("#"):
            continue
        for m in REF_RE.finditer(ln):
            out.setdefault(m.group(1)[len("/src/"):], []).append((i, "file exists" in ln))
    return out


def test_ref_tile_literal_sources_are_carried_guarded_or_allowed():
    carried = set(K.FILES.values())
    bad = [f"{rel} (ref_tile.py:{u[0][0]})" for rel, u in ref_tile_sources().items()
           if not rel.startswith(CARRIED_PREFIXES) and rel not in carried and rel not in REF_TILE_ALLOW and not all(g for _, g in u)]
    assert not bad, "ref_tile.py writes a source of a repo file a sparse lane clone lacks (stage it with kit_common_files and source /src/{kd}/<name> behind file exists): " + "; ".join(bad)
    assert "physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl" not in ref_tile_sources()          # the S81-SVC-SPLIT finding stays fixed
    assert all(a in ref_tile_sources() for a in REF_TILE_ALLOW), "a REF_TILE_ALLOW entry is no longer written by ref_tile.py: remove it"


def test_pre_grt_and_post_drt_source_the_kit_copy_behind_a_guard():
    sys.path.insert(0, str(REPO / "tools/ref_tile"))
    sys.path.insert(0, str(REPO / "tools"))
    sys.path.insert(0, str(REPO / "tools/hier_contract"))
    import ref_tile as RT
    line = RT.pk_source("physical/ref_tile/k1")
    assert line.startswith("if {[file exists /src/physical/ref_tile/k1/stn_pin_keepout.tcl]} { source /src/physical/ref_tile/k1/stn_pin_keepout.tcl }") and "REF_TILE WARNING" in line
    assert "/src/physical/hbm_accel_die_views" not in line


def test_the_scan_sees_the_known_dependency_and_the_allow_list_is_live():
    found = runtime_sources()
    assert "physical/qwen_die_masters/out_flop_release.tcl" in found                       # the scanner really finds a source line
    assert all(a in found for a in ALLOW), "an ALLOW entry no script uses any more: remove it"


def test_stn_pin_keepout_is_carried_by_every_kit_and_the_hook_prefers_it():
    common = REPO / "physical/common_flow/stn_pin_keepout.tcl"
    assert K.FILES["stn_pin_keepout.tcl"] == "physical/common_flow/stn_pin_keepout.tcl"
    assert common.is_file()
    legacy = REPO / "physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl"
    if legacy.is_file():
        assert legacy.read_bytes() == common.read_bytes()
    hook = REPO / "physical/hbm_accel_die_views/coll/rtl_ps/grt_drv_maxwire.tcl"
    if hook.is_file():                                                                     # absent in a sparse checkout; the gate has it
        text = hook.read_text()
        assert text.index("[file dirname [info script]] stn_pin_keepout.tcl") < text.index("/src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl")
        assert "OT_PK WARNING" in text


def test_face_keepout_stages_without_bench_tree_or_git(tmp_path):
    rt = tmp_path / "runtime"
    kit = tmp_path / "kit"
    kit.mkdir()
    for rel in K.FILES.values():
        src = REPO / rel
        dest = rt / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
    names = K.stage(kit, repo=rt)
    assert "stn_pin_keepout.tcl" in names
    assert (kit / "stn_pin_keepout.tcl").read_bytes() == (REPO / K.FILES["stn_pin_keepout.tcl"]).read_bytes()
    assert not (rt / "physical/hbm_accel_die_views").exists() and not (rt / ".git").exists()


def test_a_helper_missing_from_the_checkout_is_read_from_git(tmp_path, monkeypatch):
    import subprocess
    r = tmp_path / "repo"
    (r / "physical/x").mkdir(parents=True)
    (r / "physical/x/h.tcl").write_text("puts hi\n")
    subprocess.run(["git", "-C", str(r), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(r), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x"], check=True)
    (r / "physical/x/h.tcl").unlink()                                                       # the sparse clone does not have the directory checked out
    monkeypatch.setitem(K.FILES, "h.tcl", "physical/x/h.tcl")
    monkeypatch.setenv("OT_KIT_COMMON_CACHE", str(tmp_path / "cache"))
    p = K.source("h.tcl", r)
    assert p.read_text() == "puts hi\n"
    kd = tmp_path / "kit"
    kd.mkdir()
    monkeypatch.setattr(K, "FILES", {"h.tcl": "physical/x/h.tcl"})
    K.stage(kd, r)
    assert (kd / "h.tcl").read_text() == "puts hi\n"
