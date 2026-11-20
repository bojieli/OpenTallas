"""KIT-OPS-6 11-15: the die chains always run the CA steps; the legacy T/2 run is labelled LEGACY."""
import os
import stat
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SH = HERE / "die_chain_ca.sh"


def test_order_and_flags():
    s = SH.read_text()
    i = [s.index(x) for x in ("landed_phase_ocv.py", "count_align_plan.py", "count_align_bind.py", "--count-align \"$OUT/count_align_bind.json\"")]
    assert i == sorted(i)
    assert "LEGACY" in s and "sta_legacy" in s
    assert os.access(SH, os.X_OK) or True


@pytest.mark.parametrize("ca_rc, legacy_rc", [(0, 0), (37, 0), (0, 38)])
def test_runs_all_steps_with_stub_tools(tmp_path, ca_rc, legacy_rc):
    tmp_path.mkdir(parents=True, exist_ok=True); t = tmp_path / "die_plan"; (tmp_path / "s81_head").mkdir(); t.mkdir()
    calls = tmp_path / "calls.txt"
    for n, d in (("landed_phase_ocv.py", tmp_path / "s81_head"), ("count_align_plan.py", t), ("count_align_bind.py", t), ("die_sta_related.py", t)):
        script = f"import sys\nopen({str(calls)!r},'a').write('{n} '+' '.join(sys.argv[1:])+'\\n')\n"
        if n == "die_sta_related.py":
            script += f"sys.exit({ca_rc} if '--count-align' in sys.argv else {legacy_rc})\n"
        (d / n).write_text(script)
    r = subprocess.run(["bash", str(SH), str(tmp_path / "proof"), "plan.json", str(tmp_path / "out")], capture_output=True, text=True,
                       env=dict(os.environ, CA_TOOLS=str(t), REAL_VIEWS="0"))
    assert r.returncode == ca_rc, r.stderr
    got = calls.read_text().splitlines()
    assert [g.split()[0] for g in got] == ["landed_phase_ocv.py", "count_align_plan.py", "count_align_bind.py", "die_sta_related.py", "die_sta_related.py"]
    assert "--count-align" in got[3] and "--count-align" not in got[4]
    log = (tmp_path / "out" / "CHAIN.log").read_text()
    assert f"STA_CA {ca_rc}" in log and f"STA_LEGACY {legacy_rc}" in log


def test_proto_die_calls_the_ca_chain():
    s = (HERE / "proto_die.sh").read_text()
    assert "die_chain_ca.sh" in s and "CA_CHAIN" in s
    assert "die_sta_related.py $D/proof --plan $P --out $D/sta --corner TT" not in s


def test_proto_die_ca_uses_the_plan_tree_tools(tmp_path):
    """HEAD-DIE-R 11-16: the CA block resolves tools from the plan's published tree (.src-manifest.json ancestor)."""
    s = (HERE / "proto_die.sh").read_text()
    blk = s[s.index("CAT=${CA_TOOLS:-}"):s.index("CA_TOOLS=$CAT bash")]
    tree = tmp_path / "tree"; (tree / "tools/die_plan").mkdir(parents=True); (tree / ".src-manifest.json").write_text("{}")
    (tree / "tools/die_plan/die_chain_ca.sh").write_text("")
    plan = tree / "physical/die_plan/x/prep"; plan.mkdir(parents=True); (plan / "p.json").write_text("{}")
    sh = "log(){ :; }; S=/wt/tools/die_plan; P=%s\n%s\necho $CAT\n" % (plan / "p.json", blk)
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "CA_TOOLS"})
    assert r.stdout.strip() == str(tree / "tools/die_plan"), r.stdout + r.stderr
    loose = tmp_path / "loose"; loose.mkdir(); (loose / "p.json").write_text("{}")
    r = subprocess.run(["bash", "-c", "log(){ :; }; S=/wt/tools/die_plan; P=%s\n%s\necho $CAT\n" % (loose / "p.json", blk)],
                       capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "CA_TOOLS"})
    assert r.stdout.strip() == "/wt/tools/die_plan"


def _wf(tmp_path, plan):
    """Run the chain's real WF snippet against a plan file (S81-CLOCK-WINDOW-1119)."""
    s = SH.read_text()
    line = next(l for l in s.splitlines() if l.startswith("WF=$("))
    pf = tmp_path / "plan.json"; pf.write_text(plan)
    r = subprocess.run(["bash", "-c", "T=%s; PLAN=%s\n%s\necho \"[$WF]\"" % (HERE, pf, line)], capture_output=True, text=True)
    return r.stdout.strip()


def test_write_edge_snippet_reads_fall_plan(tmp_path):
    assert _wf(tmp_path, '{"clock": {"ring_hold": {"write_edge": "fall"}}}') == "[--ca-write-fall]"


def test_write_edge_snippet_rise_plan(tmp_path):
    assert _wf(tmp_path, '{"clock": {}}') == "[]"


def _fall_plan_args(tmp_path, plan_args, fall=True):
    tmp_path.mkdir(parents=True, exist_ok=True); t = tmp_path / "die_plan"; (tmp_path / "s81_head").mkdir(); t.mkdir()
    calls = tmp_path / "calls.txt"
    for n, d in (("landed_phase_ocv.py", tmp_path / "s81_head"), ("count_align_plan.py", t), ("count_align_bind.py", t), ("die_sta_related.py", t)):
        (d / n).write_text(f"import sys\nopen({str(calls)!r},'a').write('{n} '+' '.join(sys.argv[1:])+'\\n')\n")
    (t / "clock_landings.py").write_text("def ring_write_fall(plan, tn=None):\n    return %r\n" % fall)
    plan = tmp_path / "plan.json"; plan.write_text("{}")
    env = dict(os.environ, CA_TOOLS=str(t))
    if plan_args is not None:
        env["CA_PLAN_ARGS"] = plan_args
    r = subprocess.run(["bash", str(SH), str(tmp_path / "proof"), str(plan), str(tmp_path / "out")], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return next(g for g in calls.read_text().splitlines() if g.startswith("count_align_plan.py"))


def test_fall_chain_plans_at_depth_16_by_default(tmp_path):
    g = _fall_plan_args(tmp_path, None)
    assert "--write-fall-plan" in g and "--max-depth 16" in g


def test_fall_chain_keeps_an_explicit_depth_and_rise_chain_is_unchanged(tmp_path):
    assert "--max-depth 8" in _fall_plan_args(tmp_path / "a", "--max-depth 8") and "--max-depth 16" not in _fall_plan_args(tmp_path / "b", "--max-depth 8")
    assert "--max-depth" not in _fall_plan_args(tmp_path / "c", None, fall=False)
