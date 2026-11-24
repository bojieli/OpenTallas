"""BIND-EMIT-MEM 11-23: a bind with an explicit OT_BIND_EMIT_J worker count below workers x 50 GB of --mem is NOT RUN with the suggested --mem
(the S81 B1-FIX scoped bind was OOM-killed at --mem 160 with 8 workers of ~50 GB)."""
import importlib.machinery, importlib.util, os, pathlib, subprocess, sys
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_emit_mem", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_emit_mem", l)); l.exec_module(RUN)
B1 = ["env", "OT_HOLD_SAME_LEAF=1", "OT_BIND_EMIT_J=8", "bash", "/srv/x/compose/b1/gate_scoped.sh", "/srv/x/plan.json"]


def test_the_b1fix_request_is_refused_with_the_suggested_mem():
    why = RUN.emit_mem_refusal("bind", B1, 160, env={})
    assert why.startswith("BIND-EMIT-MEM") and "suggested --mem 400" in why and "OT_BIND_EMIT_J=3" in why


def test_enough_mem_auto_serial_and_override_pass():
    assert RUN.emit_mem_refusal("bind", B1, 400, env={}) == ""
    assert RUN.emit_mem_refusal("bind", ["env", "OT_BIND_EMIT_J=auto", "bash", "b.sh"], 64, env={}) == ""
    assert RUN.emit_mem_refusal("bind", ["bash", "b.sh"], 64, env={}) == ""                    # unset = auto: sized to the limit by the bind
    assert RUN.emit_mem_refusal("bind", ["env", "OT_BIND_EMIT_J=1", "bash", "b.sh"], 16, env={}) == ""
    assert RUN.emit_mem_refusal("bind", B1, 160, env={"OT_RUN_EMIT_MEM_OK": "1"}) == ""
    assert "suggested --mem 240" in RUN.emit_mem_refusal("bind", B1, 160, env={"OT_RUN_EMIT_GB_PER_WORKER": "30"})


def test_worker_count_from_environment_and_bash_c_text():
    assert RUN.emit_workers(["bash", "b.sh"], env={"OT_BIND_EMIT_J": "6"}) == 6
    assert RUN.emit_workers(["bash", "-c", "cd /x && OT_BIND_EMIT_J=14 bash bind.sh"], env={}) == 14
    assert RUN.emit_mem_refusal("", ["bash", "-c", "OT_BIND_EMIT_J=14 bash bind.sh"], 160, env={}).startswith("BIND-EMIT-MEM")   # sets workers itself: guarded without --plan-job
    assert RUN.emit_mem_refusal("", ["bash", "build.sh"], 16, env={"OT_BIND_EMIT_J": "8"}) == ""    # an inherited env on a non-bind job is not guarded


def test_cli_refuses_before_placement(tmp_path):
    e = dict(os.environ, HOME=str(tmp_path), OT_STATUS_DIR=str(tmp_path / "st"), OT_RUN_PLAN_OK="1")
    e.pop("OT_RUN_EMIT_MEM_OK", None)
    r = subprocess.run([sys.executable, "-I", str(H / "ot-run"), "--mem", "160", "--threads", "8", "--hosts", "epyc10", "--plan-job", "bind", "--rt-floor-exempt", "test",
                        "--dir", str(tmp_path), "--"] + B1, capture_output=True, text=True, env=e, timeout=120)
    assert r.returncode == RUN.NOTRUN_EXIT and "BIND-EMIT-MEM" in r.stderr and "suggested --mem 400" in r.stderr
