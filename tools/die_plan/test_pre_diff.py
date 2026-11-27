"""PRE-DIFF (COMPOSE-FAST 11-25): plan_gate_pre --base fails only on findings new against the base; base runs cached."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as G  # noqa: E402
import pre_diff as PD  # noqa: E402
from test_plan_gate_pre import mk_tree, plan  # noqa: E402


def test_diff_classifies_new_changed_inherited_gone():
    base = ["FAIL RSTREACH kv3_hg: 5 hops at /b/plan.json", "FAIL RSTREACH kv3_x: 2 hops", "FAIL TAPNAME t1: clk_t3"]
    row = ["FAIL RSTREACH kv3_hg: 5 hops at /r/row.json", "FAIL RSTREACH kv3_x: 3 hops", "FAIL R8STALE tab: 4 members"]
    d = PD.diff(row, base, PD.subs_for("/r/row.json", "/b/plan.json"), PD.subs_for("/b/plan.json"))
    assert d["inherited"] == [row[0]]
    assert d["changed"] == [row[1]]
    assert d["new"] == [row[2]]
    assert d["gone"] == [base[2]]


def _run(tmp_path, capsys, *extra):
    rc = G.main(["check", "--tree", str(tmp_path / "t"), "--plan", str(tmp_path / "row.json"),
                 "--base", str(tmp_path / "base.json"), "--json", str(tmp_path / "out.json"), *extra])
    return rc, capsys.readouterr().out, json.loads((tmp_path / "out.json").read_text())


def test_main_base_fails_only_on_new(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OT_PRE_BASE_CACHE", str(tmp_path / "cache"))
    mk_tree(tmp_path / "t")
    plan(tmp_path, keys={"band_fixed_um": 1}, name="base.json")                        # base: one unknown key (inherited)
    plan(tmp_path, keys={"band_fixed_um": 1}, name="row.json")
    rc, out, js = _run(tmp_path, capsys)
    assert rc == 0, out
    assert "LIST PRE-INHERITED SCHEMA" in out and js["findings"] == [] and len(js["inherited"]) >= 1
    assert "inherited=" in out.splitlines()[-1]
    # the row adds a second unknown key: that finding is NEW and fails; the base comes from the cache now
    plan(tmp_path, keys={"band_fixed_um": 1, "zz_new_key": 2}, name="row.json")
    rc, out, js = _run(tmp_path, capsys)
    assert rc == 1, out
    assert any("zz_new_key" in x for x in js["findings"])
    assert not any("band_fixed_um" in x and "zz_new_key" not in x for x in js["findings"])
    assert "base findings: cache" in out
    assert len(list((tmp_path / "cache").glob("*.json"))) == 1


def test_main_base_unrunnable_fails_closed(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OT_PRE_BASE_CACHE", str(tmp_path / "cache"))
    mk_tree(tmp_path / "t")
    plan(tmp_path, name="row.json")
    plan(tmp_path, name="base.json")
    rc, out, js = _run(tmp_path, capsys, "--base-tree", str(tmp_path / "no_such_tree"))
    assert rc == 1 and any(x.startswith("FAIL PRE-DIFF-UNCHECKED") for x in js["findings"]), out


def test_cache_key_moves_with_base_and_tools(tmp_path):
    t = mk_tree(tmp_path / "t")
    b = plan(tmp_path, name="base.json")
    k0 = PD.cache_key(b, t)
    b.write_text(b.read_text() + " ")
    k1 = PD.cache_key(b, t)
    (t / "tools" / "die_plan" / "extra.py").write_text("x = 1\n")
    assert len({k0, k1, PD.cache_key(b, t)}) == 3


def test_sealed_baseline_crosses_cow_attempts(tmp_path, monkeypatch):
    """Only the completed baseline moves; neither the candidate nor its paths enter the cache."""
    import os
    import shutil
    import row_gate_cow as COW

    src, rt = tmp_path / "source", tmp_path / "runtime"
    src.mkdir()
    (rt / "tools" / "die_plan").mkdir(parents=True)
    marker = src / ".src-manifest.sha256"
    marker.touch()
    marker.chmod(0o444)
    base = src / "base.json"
    base.write_text("{}")
    tool = rt / "tools" / "die_plan" / "plan_gate_pre.py"
    tool.write_text("""import json, sys
from pathlib import Path
tree = sys.argv[sys.argv.index('--tree') + 1]
result = dict(result='FAIL', findings=['FAIL TEST item in ' + tree])
Path(sys.argv[sys.argv.index('--json') + 1]).write_text(json.dumps(result))
sys.exit(1)
""")
    (rt / "tools").chmod(0o555)
    for name in ("launch1", "launch2"):
        attempt = tmp_path / name
        (attempt / "tools" / "die_plan").mkdir(parents=True)
        (attempt / ".rt_launch_ok").write_text(json.dumps(dict(src=str(src), rt=str(rt))))
        (attempt / "base.json").symlink_to(base)
        shutil.copy2(tool, attempt / "tools" / "die_plan" / tool.name)
    cache, pending, shared = (tmp_path / n for n in ("cow-cache", "pending", "shared-cache"))
    checker = tmp_path / "launch1" / "tools" / "die_plan" / tool.name
    monkeypatch.setenv("OT_PRE_BASE_CACHE", str(cache))
    monkeypatch.setenv("OT_PRE_BASE_PENDING", str(pending))
    first = PD.BaseRun("base.json", tmp_path / "launch1", checker=checker)
    findings, how = first.result()
    assert findings == [f"FAIL TEST item in {tmp_path / 'launch1'}"] and how.startswith("run ")
    COW.publish_pre_baselines(pending, shared)
    published = shared / first.cfile.name
    assert not published.stat().st_mode & 0o222
    old_inode = published.stat().st_ino
    COW.publish_pre_baselines(pending, shared)
    assert published.stat().st_ino == old_inode
    monkeypatch.setenv("OT_PRE_BASE_CACHE", str(shared))
    second = PD.BaseRun("base.json", tmp_path / "launch2", checker=checker)
    findings, how = second.result()
    assert findings == [f"FAIL TEST item in {tmp_path / 'launch2'}"] and how.startswith("cache ")
    assert second.proc is None
    scoped = PD.base_context("base.json", tmp_path / "launch2", types="different", checker=checker)
    assert first.context != scoped
    changed_env = dict(os.environ, OT_PRE_GENDRY="0")
    assert scoped != PD.base_context("base.json", tmp_path / "launch2", types="different",
                                     checker=checker, env=changed_env)


def test_unchecked_baseline_cannot_be_reused():
    assert not PD.completed_findings("FAIL", ["FAIL GEOM-UNCHECKED type missing model"])
    assert not PD.completed_findings("PASS", ["FAIL SCHEMA type bad key"])
    assert not PD.completed_findings("PASS", None)
    assert PD.completed_findings("PASS", [])
