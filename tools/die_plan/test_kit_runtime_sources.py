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


def test_the_scan_sees_the_known_dependency_and_the_allow_list_is_live():
    found = runtime_sources()
    assert "physical/qwen_die_masters/out_flop_release.tcl" in found                       # the scanner really finds a source line
    assert all(a in found for a in ALLOW), "an ALLOW entry no script uses any more: remove it"


def test_stn_pin_keepout_is_carried_by_every_kit_and_the_hook_prefers_it():
    assert K.FILES["stn_pin_keepout.tcl"] == "physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl"
    hook = REPO / "physical/hbm_accel_die_views/coll/rtl_ps/grt_drv_maxwire.tcl"
    if hook.is_file():                                                                     # absent in a sparse checkout; the gate has it
        text = hook.read_text()
        assert text.index("[file dirname [info script]] stn_pin_keepout.tcl") < text.index("/src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl")
        assert "OT_PK WARNING" in text


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
