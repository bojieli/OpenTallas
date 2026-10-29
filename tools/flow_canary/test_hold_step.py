"""FLOW-SHARED-9 (COORD 10-27 19:36 (1)): KV post-route hold step.
  - a hold-step failure is never silently replaced by the plain route: hold_step.json FAILED -> canary stage
    hold_step FAIL -> baseline REGRESSION.
    python3 -m pytest -q tools/flow_canary/test_hold_step.py"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ECO = ROOT / "physical/die_plan/qwen_kvsys/cores/harden/eco"
sys.path[:0] = [str(HERE), str(HERE.parent / "die_plan")]
import baseline as B  # noqa: E402
import canary as C  # noqa: E402


def _stage(tmp_path, run_eco_body):
    eco = tmp_path / "eco"
    eco.mkdir()
    shutil.copy(ECO / "hold_step.sh", eco / "hold_step.sh")
    (eco / "mk_eco.sh").write_text('mkdir -p "$2"; echo "OT_MAX_FANOUT=24" > "$2/variant.env"; '
                                   'echo "{}" > "$2/ECO.json"; echo "${OT_ECO_FROM:-unset}" > "$2/eco_from"\n')
    (eco / "run_eco.sh").write_text(run_eco_body)
    kit = tmp_path / "kit"
    (kit / "signoff").mkdir(parents=True)
    (kit / "signoff/signoff.json").write_text(json.dumps({"checks": {"hold_ff": {"wns_ps": -1.9}}}))
    (kit / "max_fanout.tcl").write_text("set_max_fanout 64 [current_design]\n")
    return eco, kit


def _run(eco, kit, tmp_path, env=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(["bash", str(eco / "hold_step.sh"), str(kit), str(tmp_path)], text=True,
                          capture_output=True, env=e)


def test_hold_step_failure_is_flagged_and_stale_hold_signoff_removed(tmp_path):
    eco, kit = _stage(tmp_path, 'echo "[ERROR DRT-1231] Pin u/y\\$_DFF_PN0_/RESETN does not have access point" '
                                '> "$1/run_eco.log"; echo route_finish_rc=2 > "$1/rc.txt"; exit 2\n')
    (kit / "signoff_hold").mkdir()
    (kit / "signoff_hold/signoff.json").write_text("{}")          # stale result of an earlier hold step
    r = _run(eco, kit, tmp_path)
    assert r.returncode == 2
    assert "HOLD_STEP FAILED" in r.stdout and "DRT-1231" in r.stdout
    hs = json.loads((kit / "hold_step.json").read_text())
    assert hs["status"] == "FAILED" and hs["rc"] == 2 and "DRT-1231" in hs["error"]
    assert not (kit / "signoff_hold").exists()


def test_hold_step_pass_and_not_needed_are_recorded(tmp_path):
    eco, kit = _stage(tmp_path, 'mkdir -p "$1/signoff"; echo "{\\"checks\\": {}}" > "$1/signoff/signoff.json"; exit 0\n')
    r = _run(eco, kit, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads((kit / "hold_step.json").read_text())["status"] == "PASS"
    assert (kit / "signoff_hold/signoff.json").is_file()
    (kit / "signoff/signoff.json").write_text(json.dumps({"checks": {"hold_ff": {"wns_ps": 3.0}}}))
    shutil.rmtree(Path(str(kit) + "_holdeco"))
    assert _run(eco, kit, tmp_path).returncode == 0
    assert json.loads((kit / "hold_step.json").read_text())["status"] == "NOT_NEEDED"


def test_canary_reports_failed_hold_step_and_baseline_regresses(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    (tmp_path / "canary_meta.json").write_text(json.dumps(dict(kit=str(kit), spec=dict(die="qwen_kvsys_core", item="e1"))))
    (kit / "hold_step.json").write_text(json.dumps(dict(status="FAILED", rc=2, error="[ERROR DRT-1231] x")))
    r = C.check_run(tmp_path)
    assert r["stages"]["hold_step"]["verdict"] == "FAIL" and "hold_step" in r["failing"]
    base = {"stages": {}, "contexts": {}}
    cur = {"stages": {"hold_step": "FAIL"}, "contexts": {}}
    v, rows, _ = B.compare(base, cur)
    assert v == "REGRESSION" and any(x["metric"] == "hold_step" for x in rows)
    (kit / "hold_step.json").write_text(json.dumps(dict(status="PASS", rc=0)))
    assert C.check_run(tmp_path)["stages"]["hold_step"]["verdict"] == "PASS"


# FLOW-SHARED-10 (COORD 10-27 20:53): hold repair before detailed route -- OT_HOLD_FORM=pre_drt starts the ECO from the
# kit's 5_1_grt.odb (mk_eco OT_ECO_FROM=grt), so the ECO's one detailed route never re-routes a routed DB.
def test_hold_step_form_selects_the_eco_start(tmp_path):
    eco, kit = _stage(tmp_path, 'mkdir -p "$1/signoff"; echo "{}" > "$1/signoff/signoff.json"; exit 0\n')
    d = Path(str(kit) + "_holdeco")
    for form, want in (("pre_drt", "grt"), ("post_route", "route")):
        shutil.rmtree(d, ignore_errors=True)
        r = _run(eco, kit, tmp_path, {"OT_HOLD_FORM": form})
        assert r.returncode == 0, r.stdout + r.stderr
        assert (d / "eco_from").read_text().strip() == want
        hs = json.loads((kit / "hold_step.json").read_text())
        assert hs["status"] == "PASS" and hs["form"] == form
    r = _run(eco, kit, tmp_path, {"OT_HOLD_FORM": "bogus"})
    assert r.returncode == 2 and "HOLD_STEP FAILED" in r.stdout


def _routed_kit(tmp_path):
    kit = tmp_path / "kit"
    base = kit / "run/results/asap7/hc_x/base"
    base.mkdir(parents=True)
    (base / "5_1_grt.odb").write_text("GRT")
    (base / "5_2_route.odb").write_text("ROUTED")
    (base / "6_final.spef").write_text("*SPEF")
    (kit / "config.mk").write_text("export DESIGN_NAME = x\n")
    (kit / "constraint.sdc").write_text("create_clock -period 833 [get_ports clk]\n")
    return kit, base


def test_mk_eco_grt_start_copies_the_pre_drt_db_and_records_it(tmp_path):
    kit, base = _routed_kit(tmp_path)
    for frm, src in (("grt", "GRT"), ("route", "ROUTED"), (None, "ROUTED")):
        out = tmp_path / f"eco_{frm}"
        env = dict(os.environ)
        env.pop("OT_ECO_FROM", None)
        if frm:
            env["OT_ECO_FROM"] = frm
        r = subprocess.run(["bash", str(ECO / "mk_eco.sh"), str(kit), str(out), "b3", str(ROOT)], text=True,
                           capture_output=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        assert (out / "run/results/asap7/hc_x/base/4_cts.odb").read_text() == src
        assert (out / "run/results/asap7/hc_x/base/6_final.spef").is_file()      # the repair's routed-RC basis
        assert f"OT_ECO_FROM={frm or 'route'}" in (out / "variant.env").read_text().splitlines()
        e = json.loads((out / "ECO.json").read_text())
        assert e["eco_from"] == (frm or "route") and e["source_route"].endswith("5_1_grt.odb" if frm == "grt" else "5_2_route.odb")
    (base / "5_1_grt.odb").unlink()
    r = subprocess.run(["bash", str(ECO / "mk_eco.sh"), str(kit), str(tmp_path / "eco_x"), "b3", str(ROOT)], text=True,
                       capture_output=True, env=dict(os.environ, OT_ECO_FROM="grt"))
    assert r.returncode == 2 and "lacks 5_1_grt.odb" in r.stdout


def test_hold_step_default_form_is_pre_drt(tmp_path):
    eco, kit = _stage(tmp_path, 'mkdir -p "$1/signoff"; echo "{}" > "$1/signoff/signoff.json"; exit 0\n')
    e = {k: v for k, v in os.environ.items() if k != "OT_HOLD_FORM"}
    r = subprocess.run(["bash", str(eco / "hold_step.sh"), str(kit), str(tmp_path)], text=True, capture_output=True, env=e)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (Path(str(kit) + "_holdeco") / "eco_from").read_text().strip() == "grt"
    assert json.loads((kit / "hold_step.json").read_text())["form"] == "pre_drt"


def test_ff_eco_overrides_copied_two_mode_make_assignments(tmp_path):
    kit, _ = _routed_kit(tmp_path)
    with (kit/'config.mk').open('a') as f:
        f.write('override export OT_HOLD_MM = 1\noverride export CORNERS = tc BC\n')
    out = tmp_path/'eco_ff'
    r = subprocess.run(['bash', str(ECO/'mk_eco.sh'), str(kit), str(out), 'b15', str(ROOT)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    # Evaluate make's actual precedence: CORNERS=bc on the command line alone
    # loses to the old native-kit override (the production failure).
    target = '\n.PHONY: show\nshow:\n\t@echo FRAME=$(OT_HOLD_MM):$(CORNERS)\n'
    (out/'check.mk').write_text((out/'config.mk').read_text() + target)
    actual = subprocess.check_output(['make', '-s', '-f', str(out/'check.mk'), 'show', 'CORNERS=tc BC'], text=True)
    assert actual.strip() == 'FRAME=0:bc'
    hook = (out/'eco_post.tcl').read_text()
    assert hook.index('source /work/kit_modes_eco.tcl') < hook.index('source /work/eco_route.tcl')
    assert 'kit_modes_eco_done' in hook
    assert (out/'kit_modes_eco.tcl').is_file()
