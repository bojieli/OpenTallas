import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hook_manifest


def test_manifest_classes(tmp_path):
    tree, main, kit = tmp_path / "tree", tmp_path / "main", tmp_path / "kit"
    for d in (tree, main, kit):
        d.mkdir()
    (tree / "a.tcl").write_text("old\n"); (kit / "a.tcl").write_text("old\n"); (main / "a.tcl").write_text("new\n")   # stale
    (tree / "b.tcl").write_text("loc\n"); (kit / "b.tcl").write_text("loc2\n"); (main / "b.tcl").write_text("m\n")    # kit patched after gen
    (tree / "c.py").write_text("same\n"); (kit / "c.py").write_text("same\n"); (main / "c.py").write_text("same\n")
    (kit / "gen_only.py").write_text("x\n")
    doc = hook_manifest.write(kit, tree, main_sha="abc")
    assert set(doc["hooks"]) == {"a.tcl", "b.tcl", "c.py"}
    rows = {r["hook"]: r["cls"] for r in hook_manifest.check(kit, main)}
    assert rows == {"a.tcl": "stale", "b.tcl": "local"}
    r = subprocess.run([sys.executable, str(HERE / "hook_manifest.py"), "check", str(kit), "--main", str(main), "--strict"],
                       capture_output=True, text=True)
    assert r.returncode == 3 and "MANIFEST stale a.tcl" in r.stdout


def test_gen_phys_wiring_is_flag_gated():
    t = (HERE / "gen_phys.py").read_text()
    assert "merge_census.on" in t and "hop_census.on" in t and "hook_manifest.write" in t and "OT_HOOK_MANIFEST" in t
    # off by default: flag files only written for 1/warn
    assert 'os.environ.get("OT_MERGE_CENSUS", "0")' in t and 'os.environ.get("OT_HOP_CENSUS", "0")' in t


def test_merge_census_gate_exit(tmp_path):
    k = tmp_path / "k"; b = k / "run/results/asap7/d/base"; b.mkdir(parents=True)
    # no inputs -> NOINPUT row, 0 missing, gate passes
    r = subprocess.run([sys.executable, str(HERE / "merged_replica_census.py"), str(k), "--gate", "64"], capture_output=True, text=True)
    assert r.returncode == 0 and "OT_MERGE_CENSUS PASS missing=0" in r.stdout
    r = subprocess.run([sys.executable, str(HERE / "merged_replica_census.py"), str(k), "--gate", "0"], capture_output=True, text=True)
    assert r.returncode == 4
