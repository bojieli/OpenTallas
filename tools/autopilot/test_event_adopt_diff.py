"""ADOPT-CENSUS-1800: event_adopt_diff three-way classes, proven-fix ledger, carry pack."""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import event_adopt_diff as AD  # noqa: E402


def g(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout.strip()


def commit(repo, files, msg):
    for p, txt in files.items():
        f = repo / p
        if txt is None:
            f.unlink()
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(txt)
    g(repo, "add", "-A")
    g(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg)
    return g(repo, "rev-parse", "HEAD")


def setup(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    g(repo, "init", "-q")
    pin = commit(repo, {"tools/a.py": "a0\n", "tools/b.py": "b0\n1\n2\n3\n4\n5\nz\n", "tools/c.py": "c0\n", "rtl/r.sv": "r0\n",
                        "physical/die_plan/s81/p.json": "{}\n", "physical/die_plan/kv/k.json": "{}\n", "tools/gone.py": "g\n"}, "pin")
    fix = commit(repo, {"tools/b.py": "b0\n1\n2\n3\n4\n5\nFIX\n"}, "fix b")
    commit(repo, {"tools/a.py": "a1\n", "tools/c.py": "c1\n", "tools/new.py": "n\n", "physical/die_plan/kv/k.json": "{1}\n",
                  "tools/gone.py": None}, "main moves")
    main = g(repo, "rev-parse", "HEAD")
    tree = tmp_path / "tree"
    for p, txt in {"tools/a.py": "a0\n", "tools/b.py": "EV\n1\n2\n3\n4\n5\nz\n", "tools/c.py": "c1\n", "rtl/r.sv": "r-event\n",
                   "physical/die_plan/s81/p.json": "{}\n", "physical/die_plan/kv/k.json": "{}\n", "tools/gone.py": "g\n"}.items():
        (tree / p).parent.mkdir(parents=True, exist_ok=True)
        (tree / p).write_text(txt)
    (tree / AD.MANIFEST).write_text(json.dumps({"main_sha": pin, "overlay": {"tools/b.py": "x", "tools/c.py": "y", "rtl/r.sv": "z"},
                                                "files": {}, "scope": ["tools", "rtl", "physical"], "manifest_hash": "h0"}))
    return repo, tree, pin, fix, main


def run_diff(tmp_path, repo, tree, ledger="", extra=()):
    out = tmp_path / "out"
    rc = AD.main(["diff", "--tree", str(tree), "--repo", str(repo), "--main", "HEAD", "--die", "s81", "--out", str(out),
                  "--ledger", ledger, *extra])
    assert rc == 0
    return json.loads((out / "adopt_diff.json").read_text())


def test_three_way_classes(tmp_path):
    repo, tree, pin, fix, main = setup(tmp_path)
    rep = run_diff(tmp_path, repo, tree)
    cls = {r["path"]: r["cls"] for r in rep["rows"]}
    assert cls["tools/a.py"] == "LAG"            # event untouched, main moved: carried automatically
    assert cls["tools/new.py"] == "LAG"          # added on main
    assert cls["tools/gone.py"] == "LAG"         # deleted on main
    assert cls["tools/b.py"] == "BOTH"           # event edited, main fixed: the die owner's list
    assert cls["tools/c.py"] == "CURRENT"        # already carried by hand
    assert "physical/die_plan/kv/k.json" not in cls   # another die's plan dir is out of the s81 scope
    assert "rtl/r.sv" not in cls                 # event-only delta, main did not touch it
    assert rep["pin"] == pin and rep["main"] == main and rep["main_commits"] == 2
    both = next(r for r in rep["rows"] if r["path"] == "tools/b.py")
    assert any("fix b" in c for c in both["commits"])
    assert "LAG 3" in rep["summary"] and "BOTH 1" in rep["summary"]


def test_ledger_commit_and_define_rows(tmp_path):
    repo, tree, pin, fix, main = setup(tmp_path)
    kit = tmp_path / "kit/gen/lepe_mu_LP__t1"
    kit.mkdir(parents=True)
    (kit / "config.mk").write_text("export DESIGN_NAME = x\nexport VERILOG_DEFINES = -DSYNTHESIS -DOT_S81SL_LEP_CRP2\n")
    led = tmp_path / "led.tsv"
    led.write_text("id\tkind\tsha\tdie\ttypes\tvalue\tnote\n"
                   f"fixb\tcommit\t{fix[:10]}\ts81\t*\t\tb fix\n"
                   f"rip1\tdefine\t{fix[:10]}\ts81\tlepe_*_LP__*\tOT_S81SL_LEP_RIP1\tregistered read\n"
                   f"crp2\tdefine\t{fix[:10]}\ts81\tlepe_*_LP__*\tOT_S81SL_LEP_CRP2\t\n"
                   f"other\tcommit\t{fix[:10]}\tkv\t*\t\tnot this die\n")
    rep = run_diff(tmp_path, repo, tree, str(led), ["--kit", str(tmp_path / "kit/gen/lepe_mu_LP__t1"), "--tools-sha", "j5tree"])
    v = {r["id"]: r for r in rep["ledger"]}
    assert set(v) == {"fixb", "rip1", "crp2"}
    assert v["fixb"]["verdict"] == "MISSING" and "tools/b.py" in v["fixb"]["missing"]   # event copy has the pre-fix hunk
    assert "UNRESOLVED" in v["fixb"]["tools_pin"]                                         # a label is not a pin
    assert v["rip1"]["verdict"] == "MISSING" and v["rip1"]["source"] == ["config.mk"]
    assert v["crp2"]["verdict"] == "CARRIED"


def test_commit_row_carried_in_an_edited_file(tmp_path):
    repo, tree, pin, fix, main = setup(tmp_path)
    (tree / "tools/b.py").write_text("EV\n1\n2\n3\n4\n5\nFIX\n")      # event edit + the fix hunk: reverse-applies
    led = tmp_path / "led.tsv"
    led.write_text(f"fixb\tcommit\t{fix}\t*\t*\t\t\n")
    rep = run_diff(tmp_path, repo, tree, str(led), ["--tools-sha", main])
    r = rep["ledger"][0]
    assert r["verdict"] == "CARRIED" and r["tools_pin"] == "HAS"


def test_bare_name_selector_counts():
    assert AD.has_define({"RIP1"}, "OT_S81SL_LEP_RIP1")
    assert not AD.has_define({"OT_X_RIP2"}, "OT_S81SL_LEP_RIP1")


def test_carry_pack_takes_lag_files_from_main(tmp_path):
    repo, tree, pin, fix, main = setup(tmp_path)
    run_diff(tmp_path, repo, tree)
    pack = tmp_path / "pack"
    assert AD.main(["carry", "--report", str(tmp_path / "out/adopt_diff.json"), "--repo", str(repo), "--pack", str(pack)]) == 0
    d = json.loads((pack / "delta.json").read_text())
    assert set(d["add"]) == {"tools/a.py", "tools/new.py"} and d["delete"] == ["tools/gone.py"]
    assert (pack / "files/tools/a.py").read_text() == "a1\n"
    assert d["new_main"] == main and d["overlay_drop"] == ["tools/c.py"] and d["both"] == ["tools/b.py"]
    assert d["old_manifest_hash"] == "h0"
    assert AD.main(["carry", "--report", str(tmp_path / "out/adopt_diff.json"), "--repo", str(repo), "--pack", str(pack)]) == 2


def test_label_pin_is_refused(tmp_path):
    repo, tree, pin, fix, main = setup(tmp_path)
    assert AD.main(["diff", "--tree", str(tree), "--repo", str(repo), "--main", "HEAD", "--pin", "j5tree", "--ledger", ""]) == 2


def test_repo_ledger_parses():
    rows = AD.read_ledger(AD.LEDGER)
    ids = {r["id"] for r in rows}
    assert {"hwin-8e20268b5d83", "rip1-define", "slew-25fc65d0cb1", "reset-legs-f02ccd50eb", "reset-cap-ecd0239bd5",
            "s81-prefix-d98908b665", "schema-8e9cdd615c"} <= ids
    assert any(r["id"].startswith("lockup") for r in rows)
    assert all(r["kind"] in ("commit", "define", "key") for r in rows)
