"""CANCEL-STOP-1119: ot-run --cancel also stops the started job (ot-heavy-stop --match <its --dir>) on the client's hosts."""
import importlib.machinery, importlib.util, pathlib, types
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_cancel_stop", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_cancel_stop", l)); l.exec_module(RUN)


def test_targets_use_the_clients_dir_and_hosts():
    hit = {1: (["--mem", "48", "--hosts", "epyc2,epyc7", "--dir", "/srv/opentallas-scratch2/claude/x/kit1", "--", "bash", "run_kit.sh"], "/srv/opentallas-scratch2/claude/x/kit1")}
    assert RUN.stop_targets(hit, "kit1", ["epyc8"]) == [("epyc2", "/srv/opentallas-scratch2/claude/x/kit1"), ("epyc7", "/srv/opentallas-scratch2/claude/x/kit1")]


def test_generic_job_root_falls_back_to_the_substring_and_short_matches_stop_nothing():
    hit = {1: (["--mem", "4", "--", "bash", "a"], RUN.JOB_ROOT)}
    assert RUN.stop_targets(hit, "t27keep_grt", ["epyc8", "epyc9"]) == [("epyc8", "t27keep_grt"), ("epyc9", "t27keep_grt")]
    assert RUN.stop_targets(hit, "ab", ["epyc8"]) == []


def test_stop_started_runs_ot_heavy_stop_over_ssh():
    calls = []
    RUN.stop_started([("epyc2", "/x/kit one")], run=lambda cmd, **k: (calls.append(cmd), types.SimpleNamespace(stdout="ot-heavy-stop: 1 scope(s) stopped\n", stderr=""))[1])
    assert calls[0][-2] == "epyc2" and calls[0][-1] == "ot-heavy-stop --match '/x/kit one'"
