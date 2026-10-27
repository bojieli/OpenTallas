"""GEN-FIX-1 (10-27): the three older core-kit generators build kits on THIS checkout's tools/die_plan.

hbm/cores/harden/gen_core_kit.py, s81/cores/eng/gen_core_kit.py and s81/cores/svc/gen_core_kit_s81.py used to
default --tool to deleted 10-23 worktrees and to anchor on the pre-10-24 `set ff_skip_re {...}` line of
face_flops.tcl (main 6c39897574 widened it).  Per generator: default-tool kit generation rc0, the kit's
face_flops.tcl = main face_flops.tcl + only the generator's own patches (skip set, unreg-pin audit),
face_flops_release.tcl = main's byte for byte, and master_slice check-kit PASS on a kit built with a core slice.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DP = ROOT / "physical/die_plan"
sys.path.insert(0, str(HERE))
import master_slice as MS  # noqa: E402

GENS = {
    "hbm_harden": (DP / "hbm/cores/harden", "gen_core_kit.py",
                   ["--plan", str(DP / "hbm/die_plan.json"), "--type", "ot_hbm_sm_attn_tile_tp__362.88x406.08",
                    "--recipes", str(DP / "hbm/cores/harden/recipes.json")], DP / "hbm/die_plan.json"),
    "s81_eng": (DP / "s81/cores/eng", "gen_core_kit.py", ["--core", "e"], None),
    "s81_svc": (DP / "s81/cores/svc", "gen_core_kit_s81.py",
                ["--cores", str(DP / "s81/cores/svc/cores_svc.json"), "--plan", str(DP / "s81/die_plan.json"),
                 "--recipes", str(DP / "s81/cores/svc/recipes.json")], DP / "s81/die_plan.json"),
}


def _gen(name, out, *extra):
    d, script, args, _ = GENS[name]
    if not (d / script).is_file():
        pytest.skip(f"{d / script} not in this checkout")
    r = subprocess.run([sys.executable, script, *args, "--out", str(out), *extra], cwd=d, capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    kd = Path(json.loads(r.stdout.strip().splitlines()[-1])["kit"])
    assert kd.is_dir()
    return kd


def _core_slice(sd, fz, plan_path):
    plan = json.loads(plan_path.read_text()) if plan_path else None
    sl = {"schema": MS.SCHEMA, "die": "test", "kind": "core", "type": fz["module"], "module": fz["module"],
          "instances": ["u0"], "plan": "test", "plan_sha256": "aa",
          "master_plan_sha256": MS.plan_sha(plan) or "mp1", "frozen": True, "outline_um": fz["outline_um"],
          "keepouts": [], "islands": [], "bays": [], "entry_pins": [], "hard_cores": [],
          "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 40, "early_taps": False},
          "corridors": [], "gates": {"reach": "NOT RUN"}}
    assert MS.validate(sl) == []
    sd.mkdir(parents=True, exist_ok=True)
    (sd / f"{fz['module']}.json").write_text(json.dumps(sl, indent=1))


@pytest.mark.parametrize("name", sorted(GENS))
def test_kit_on_main_tool(name, tmp_path, monkeypatch):
    monkeypatch.delenv("OT_MASTER_PLAN_REQUIRED", raising=False)
    kd = _gen(name, tmp_path / "k")
    fz = json.loads((kd / "freeze.json").read_text())
    if "tool" in fz:
        assert fz["tool"].split("@")[0] == str(ROOT / "tools/die_plan")
    main_ff = (HERE / "face_flops.tcl").read_text()
    ff = (kd / "face_flops.tcl").read_text()
    skip = "^(" + "|".join(re.escape(n) for n in fz["clocks"] + fz["resets"]) + ")$"
    assert re.findall(r"^set ff_skip_re \{.*$", ff, re.M) == ["set ff_skip_re {" + skip + "}"]
    # undo the generator's own patches -> main face_flops.tcl byte for byte (no stale tool copy)
    back = ff.replace("set ff_skip_re {" + skip + "}", re.findall(r"^set ff_skip_re \{.*$", main_ff, re.M)[0])
    back = back.replace("\nset ff_unreg [open $::env(RESULTS_DIR)/ot_unreg_pins.txt w]", "")
    back = back.replace('incr ff_miss; puts $ff_unreg "$pass\\t$nm"; continue', "incr ff_miss; continue")
    assert back == main_ff
    assert (kd / "face_flops_release.tcl").read_bytes() == (HERE / "face_flops_release.tcl").read_bytes()
    # with a frozen core slice: the kit consumes it and the static kit-vs-slice gate passes
    _core_slice(tmp_path / "s", fz, GENS[name][3])
    kd2 = _gen(name, tmp_path / "k2", "--master-slice", str(tmp_path / "s"))
    assert json.loads((kd2 / "freeze.json").read_text())["master_plan"]["frozen"] is True
    rep = MS.check_kit(kd2)
    assert rep["verdict"] == "PASS", rep["issues"]
    r = subprocess.run([sys.executable, str(HERE / "master_slice.py"), "check-kit", str(kd2)], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr
