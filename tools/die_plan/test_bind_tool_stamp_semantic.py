"""SEMANTIC-TOOLSKEW-1122 (COORD 21:0x): a reset-generator hash difference is accepted when the new rt's reset solve reproduces the
bound tree, and refused (naming generator / tree fields) on a real difference, a missing receipt, a solve error or an unexercised
generator.  Shape of tonight's case: S81 dsdv_slice_lepw_mus_LP__t2 (FABLE-FIX-CONE-SCATTER), reset_tree/reset_anchor/... differ,
the 51fdaae7793b and current rt solves both equal the bound tree at cap 300 (measured on epyc8)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "bind_tool_stamp.py"
T = "dsdv_slice_lepw_mus_LP__t2"
TREE = {"type": T, "entry": "sync", "sync_stages": 2, "relays": [{"id": "r0", "xy": [1, 2]}], "core_resets": [{"pin": "a"}]}

STUBS = {
    "schema.py": "class Plan:\n    def __init__(self, raw, path=None):\n        self.raw = raw\n",
    "cbc_rules.py": "import contextlib\n@contextlib.contextmanager\ndef bound_reset_hop_cap(c):\n    yield\n",
    "bound_reset_contract.py": "LEGACY_CAPS = (300.0,)\ndef reach_cap_um(x):\n    return (x or {}).get('reach_cap_um')\n",
    "reset_tree.py": "import json, os\nimport reset_anchor\ndef for_type(P, tn):\n"
                     "    if P.raw.get('boom'):\n        raise ValueError('solve failed')\n"
                     "    t = json.loads(json.dumps(P.raw['tree']))\n    t['core_resets'][0]['physical_inst'] = 'u_x'\n    return t\n",
    "reset_anchor.py": "X = 1\n",
}


def setup(tmp, plan_tree=TREE, receipt=True, boom=False):
    root = tmp / "rt"
    d = root / "tools" / "die_plan"
    d.mkdir(parents=True)
    for n, txt in STUBS.items():
        (d / n).write_text(txt)
    (d / "bind_tool_stamp.py").write_text(TOOL.read_text())
    bo = tmp / "bind"
    (bo / "rtl").mkdir(parents=True)
    # the bind ran with OTHER reset_tree / reset_anchor bytes
    gens = {n: "0" * 64 for n in ("reset_tree.py", "reset_anchor.py")}
    (bo / "bind_tool.json").write_text(json.dumps({"tools_sha": "51fdaae7793b", "generators": gens}))
    if receipt:
        (bo / "rtl" / f"s81p_{T}.reset_tree.json").write_text(json.dumps({"plan_type": T, "tree": TREE, "reach_cap_um": 300.0}))
    plan = tmp / "plan.json"
    plan.write_text(json.dumps({"tree": plan_tree, "boom": boom}))
    return root, bo, plan


def run(root, bo, plan, sem=True):
    argv = [sys.executable, "-I", str(root / "tools/die_plan/bind_tool_stamp.py"), "check", "--bind-out", str(bo), "--tools", str(root)]
    if sem:
        argv += ["--plan", str(plan), "--type", T]
    return subprocess.run(argv, capture_output=True, text=True)


def test_identical_solve_is_accepted(tmp_path):
    r = run(*setup(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "BIND-GEN-TOOLSKEW ok semantic" in r.stdout and T in r.stdout


def test_hash_rule_without_plan(tmp_path):
    r = run(*setup(tmp_path), sem=False)
    assert r.returncode == 3 and "reset_anchor.py, reset_tree.py" in r.stdout and "Semantic" not in r.stdout


def test_real_difference_refused_with_fields(tmp_path):
    other = dict(TREE, relays=[{"id": "r0", "xy": [1, 3]}])
    r = run(*setup(tmp_path, plan_tree=other))
    assert r.returncode == 3 and "Semantic replay refused" in r.stdout and "relays (1 vs 1 rows, 1 differ)" in r.stdout


def test_missing_receipt_and_solve_error_fail_closed(tmp_path):
    r = run(*setup(tmp_path / "a", receipt=False))
    assert r.returncode == 3 and "no bound reset receipt" in r.stdout
    r = run(*setup(tmp_path / "b", boom=True))
    assert r.returncode == 3 and "raised" in r.stdout


def test_unexercised_generator_is_named_in_the_note(tmp_path):
    root, bo, plan = setup(tmp_path)
    st = json.loads((bo / "bind_tool.json").read_text())
    st["generators"]["kit_relay_depth.py"] = "0" * 64
    (root / "tools/die_plan/kit_relay_depth.py").write_text("X = 2\n")
    (bo / "bind_tool.json").write_text(json.dumps(st))
    r = run(root, bo, plan)
    assert r.returncode == 0, r.stdout
    assert "exercised and identical:" in r.stdout and "reset_anchor.py, reset_tree.py; not re-derived" in r.stdout
    assert "not re-derived against the bind at gen: kit_relay_depth.py" in r.stdout
