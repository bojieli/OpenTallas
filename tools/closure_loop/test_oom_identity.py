"""OOM attribution needs a process incarnation or independent run ownership."""
import ast
import os
from pathlib import Path

source = Path(__file__).with_name("closure_loop.py")
tree = ast.parse(source.read_text())
script = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "OOM_IDENTITY_SCRIPT" for t in n.targets))
ns = {"__name__": "oom_identity_test"}
exec(compile(script, str(source) + ":OOM_IDENTITY_SCRIPT", "exec"), ns)
def attribute(events, samples, run):
    return ns["attribute"](events, samples, run, "route.a1")
RUN = "/scratch/closure-loop/actual-stage"
CG = "/user.slice/user-1000.slice/user@1000.service/app.slice/stage-42.scope"
OTHER = "/user.slice/user-1000.slice/user@1000.service/app.slice/dq12-1022074.scope"


def sample(birth=100, observed=150, cg=CG, boot="boot"):
    return dict(pid=1022170, boot_id=boot, start_ticks=birth, birth_us=birth,
                observed_us=observed, cgroups=[cg], exclusive_cgroups=[cg])


def event(msg, at=200, boot="boot"):
    return dict(MESSAGE=msg, __REALTIME_TIMESTAMP=str(at), _BOOT_ID=boot)


def kernel(cg=CG):
    return [event("oom-kill:task_memcg=" + cg + ",task=verilator_bin,pid=1022170,uid=1000", 199),
            event("Memory cgroup out of memory: Killed process 1022170 (verilator_bin)")]


def test_kernel_incarnation_and_cgroup_positive():
    owned, unknown = attribute(kernel(), [sample()], RUN)
    assert len(owned) == 1 and not unknown


def test_reused_pid_after_historical_event_refused():
    # The old union-of-PIDs implementation accepts this unrelated historical kill.
    samples = [sample(birth=1000, observed=1100)]
    assert 1022170 in {s["pid"] for s in samples}
    owned, unknown = attribute(kernel(OTHER), samples, RUN)
    assert not owned and len(unknown) == 1


def test_actual_dq12_cgroup_mismatch_refused():
    owned, unknown = attribute(kernel(OTHER), [sample()], RUN)
    assert not owned and unknown[0]["reason"] == "target cgroup mismatch"


def test_first_sample_after_event_has_no_retroactive_ownership():
    assert not attribute(kernel(), [sample(observed=201)], RUN)[0]


def test_previous_boot_pid_refused():
    assert not attribute(kernel(), [sample(boot="previous")], RUN)[0]


def test_earlyoom_real_runpath_independent_positive():
    e = event('sending SIGKILL to process 1022170 uid 1000 "python3 ' + RUN + '/cl/route.a1.sh"')
    assert attribute([e], [], RUN) == ([e["MESSAGE"]], [])


def test_earlyoom_pid_only_preserved_unattributed():
    e = event('sending SIGTERM to process 1022170 uid 1000 "verilator_bin"')
    owned, unknown = attribute([e], [sample()], RUN)
    assert not owned and unknown[0]["event"] == e


def test_missing_time_preserved_and_runpath_prefix_not_substring():
    e = event('sending SIGTERM to process 1022170 "python ' + RUN + '-other/a.py"')
    assert not attribute([e], [], RUN)[0]
    del e["__REALTIME_TIMESTAMP"]
    assert attribute([e], [], RUN)[1][0]["reason"] == "missing event identity/time"


def test_shared_user_cgroup_is_not_independent_ownership():
    assert not attribute(kernel("/user.slice"), [sample(cg="/user.slice")], RUN)[0]


def test_native_capture_records_actual_birth_and_cgroup():
    records = list(ns["capture"]([str(os.getpid())]))
    assert len(records) == 1
    r = records[0]
    ticks = int(Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19])
    assert r["pid"] == os.getpid() and r["start_ticks"] == ticks
    assert r["birth_us"] <= r["observed_us"] and r["cgroups"]
    assert r["boot_id"] == Path("/proc/sys/kernel/random/boot_id").read_text().strip().replace("-", "")
    assert len(r["boot_id"]) == 32  # journald _BOOT_ID omits /proc UUID hyphens


def test_shared_session_scope_is_not_stage_ownership():
    s = sample()
    s["exclusive_cgroups"] = []
    assert not attribute(kernel(), [s], RUN)[0]


def test_kernel_context_is_not_reused_for_later_earlyoom_pid():
    events = kernel() + [event('sending SIGTERM to process 1022170 "verilator_bin"', 400)]
    owned, unknown = attribute(events, [sample()], RUN)
    assert len(owned) == 1 and len(unknown) == 1


def test_kernel_companion_is_consumed_once():
    events = kernel() + [event('Memory cgroup out of memory: Killed process 1022170 (vvp)', 400)]
    owned, unknown = attribute(events, [sample()], RUN)
    assert len(owned) == 1 and len(unknown) == 1


def test_actual_sibling_bench_and_generic_run_paths_do_not_own_route():
    for path in (RUN + "/cl/bench_bfcol_txn_positive.a1b1.sh", RUN + "/bench_c199/positive/obj/verilator_bin",
                 RUN + "/cl/route.a10.sh", RUN + "/cl/route.a1.sh.backup",
                 "/somewhere" + RUN + "/cl/route.a1.sh",
                 "/somewhere~" + RUN + "/cl/route.a1.sh",
                 "/somewhere:" + RUN + "/cl/route.a1.sh"):
        e = event('sending SIGTERM to process 1022170 uid 1000 "bash ' + path + '"')
        owned, unknown = attribute([e], [], RUN)
        assert not owned and len(unknown) == 1, path


def test_shipped_helper_cli_preserves_owned_and_unknown_records(tmp_path):
    import json
    import subprocess
    import sys
    helper = tmp_path / "oom_identity.py"
    helper.write_text(script)
    journal, samples = tmp_path / "journal", tmp_path / "samples"
    owned, unknown = tmp_path / "owned", tmp_path / "unknown"
    events = [event('sending SIGKILL to process 1022170 "bash ' + RUN + '/cl/route.a1.sh"'),
              event('sending SIGTERM to process 1022170 "python ' + RUN + '/bench_c199/positive/obj/Vtest"')]
    journal.write_text("".join(json.dumps(e) + "\n" for e in events))
    samples.write_text("")
    subprocess.run([sys.executable, str(helper), "attribute", str(journal), str(samples), RUN,
                    str(owned), str(unknown), "route.a1"], check=True)
    assert owned.read_text().splitlines() == [events[0]["MESSAGE"]]
    assert json.loads(unknown.read_text())["event"] == events[1]


def test_missing_old_kill_cannot_reuse_companion_before_new_pid_birth():
    old = kernel()[0]
    old["__REALTIME_TIMESTAMP"] = "50"
    # The old kill is absent (journal loss). A new sampled incarnation begins
    # at100; matching cgroup text from50 cannot prove ownership of the kill200.
    later = kernel()[1]
    owned, unknown = attribute([old, later], [sample(birth=100, observed=150)], RUN)
    assert not owned and len(unknown) == 1
