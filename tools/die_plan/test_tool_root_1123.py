"""TOOLROOT-1123: the running tools root must be the declared rt sha (name + manifest content), fail closed."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tool_root as TR  # noqa: E402

SHA = "ab" * 20


def rt(tmp, sha=SHA, body="x = 1\n"):
    r = tmp / "rt"
    d = r / sha[:12] / "tools" / "die_plan"
    d.mkdir(parents=True)
    (d / "m.py").write_text(body)
    (r / f"{sha[:12]}.manifest.json").write_text(json.dumps(
        {"sha": sha, "files": {"tools/die_plan/m.py": hashlib.sha256(b"x = 1\n").hexdigest(), "README": "0"}}))
    return r, r / sha[:12]


def test_pass_on_declared_snapshot(tmp_path):
    r, root = rt(tmp_path)
    assert TR.check(SHA, root, env={}, rt_roots=(str(r),)) == []
    assert TR.check(None, root, env={"OT_RT_CURRENT": str(root)}, rt_roots=(str(r),)) == []
    assert TR.check(None, root, env={"OT_TOOLS_SHA": SHA[:12]}, rt_roots=(str(r),)) == []


def test_wrong_root_fails_closed(tmp_path):
    r, root = rt(tmp_path)
    other = "cd" * 20
    f = TR.check(other, root, env={}, rt_roots=(str(r),))
    assert any(x.startswith("FAIL TOOLROOT tools root") and "declared rt cdcdcdcdcdcd" in x for x in f)
    assert any("no rt manifest" in x for x in f)
    plain = tmp_path / "plain"
    (plain / "tools" / "die_plan").mkdir(parents=True)
    assert any("no resolvable sha" in x for x in TR.check(SHA, plain, env={}, rt_roots=(str(r),)))
    assert TR.check(None, root, env={"OT_TOOLS_SHA": "j5tree"}, rt_roots=(str(r),))[0].startswith("FAIL TOOLROOT")


def test_hand_patched_copy_fails_content(tmp_path):
    r, root = rt(tmp_path, body="x = 2\n")
    f = TR.check(SHA, root, env={}, rt_roots=(str(r),))
    assert len(f) == 1 and f[0].startswith("FAIL TOOLROOT-CONTENT") and "tools/die_plan/m.py" in f[0]


def test_undeclared_is_advisory_or_silent(tmp_path):
    r, root = rt(tmp_path)
    assert TR.check(None, root, env={}, rt_roots=(str(r),), quiet_undeclared=True) == []
    assert TR.check(None, root, env={}, rt_roots=(str(r),))[0].startswith("WARN TOOLROOT-ADVISORY")


def test_plan_gate_pre_knows_the_class():
    import plan_gate_pre as P
    assert "TOOLROOT" in P.CLASSES
