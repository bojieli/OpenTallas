"""KIT-OPS-6 11-15 (COORD): ot-run skips hosts that lack the job's input paths; refuses (exit 78) when none has them; --replicate copies small dirs."""
from importlib.machinery import SourceFileLoader
from pathlib import Path

M = SourceFileLoader("ot_run_needs", str(Path(__file__).with_name("ot-run"))).load_module()
SRC = "/srv/opentallas-scratch2/claude/lane/src"
PLAN = SRC + "/plan.json"
RUN = "/srv/opentallas-scratch2/claude/lane/run"


def fake(held):
    def probe(host, paths):
        return {p: p in held.get(host, set()) for p in paths}
    return probe


def test_cmd_input_paths_skip_run_dir_and_outputs():
    cmd = ["bash", "-c", f"python3 {SRC}/tools/gen.py {PLAN} --out {RUN}/o.json > {RUN}/log"]
    got = M.cmd_input_paths(["python3", f"{SRC}/tools/gen.py", PLAN, "--out", "/srv/opentallas-scratch2/claude/lane/outdir"], RUN)
    assert got == [SRC + "/tools/gen.py", PLAN]
    assert M.cmd_input_paths(["cat", RUN + "/x"], RUN) == []


def test_host_without_the_input_tree_is_skipped():
    probe = fake({"epyc9": {SRC + "/tools/gen.py", PLAN}, "epyc10": {PLAN}})
    kept, miss = M.hosts_with_needs(["epyc10", "epyc9", "epyc2"], [], [SRC + "/tools/gen.py", PLAN], probe)
    assert kept == ["epyc9"]
    assert miss["epyc10"] == [SRC + "/tools/gen.py"] and miss["epyc2"][0] == SRC + "/tools/gen.py"


def test_a_path_that_exists_nowhere_is_an_output_not_a_need():
    probe = fake({"a": {PLAN}, "b": {PLAN}})
    kept, miss = M.hosts_with_needs(["a", "b"], [], [PLAN, "/srv/opentallas-scratch2/claude/lane/newout"], probe)
    assert kept == ["a", "b"] and not miss


def test_explicit_needs_must_exist_and_none_holding_is_reported():
    probe = fake({"a": set(), "b": set()})
    kept, miss = M.hosts_with_needs(["a", "b"], [SRC], [], probe)
    assert kept == [] and set(miss) == {"a", "b"}


def test_replicate_copies_to_hosts_lacking_the_dir():
    calls = []
    probe = fake({"a": {SRC}, "b": set()})
    out = M.replicate_dirs([SRC], ["a", "b"], probe, lambda argv: calls.append(argv[2]) or 0)
    assert out == [("a", "b", 0)] and "--keep-old-files" in calls[0] and "ssh -o BatchMode=yes a" in calls[0]


def test_main_wires_needs_and_refusal():
    s = (Path(__file__).with_name("ot-run")).read_text()
    assert '"--needs"' in s and '"--replicate"' in s and "sys.exit(78)" in s and "OT_RUN_NO_NEEDS_CHECK" in s


def test_staged_paths_are_not_demanded_of_the_host():
    s = (Path(__file__).with_name('ot-run')).read_text()
    assert 'x.startswith(t + "/") for t in STAGE' in s
