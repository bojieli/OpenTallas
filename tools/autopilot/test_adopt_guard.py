"""KIT-OPS-6 11-14: adopt_guard finds manifest inputs missing on a wave host, copies them from a host that has them, fails closed otherwise."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adopt_guard as G  # noqa: E402

F1 = "/srv/opentallas-scratch2/claude/kv-102/cg3/kv_out15/rtl/a.sv"
F2 = "/srv/opentallas-scratch2/claude/kv-102/cg3/kv_out15/rtl/b.sv"


def fake(have):
    """run(argv): `test -e` probes answer from have {host: set(files)}; the copy pipe adds the file to the target host"""
    log = []

    def run(argv, timeout=900):
        if argv[:2] == ["bash", "-c"]:                      # the copy pipeline
            line = argv[2]
            f = "/" + line.split("-cf - ")[1].split()[0].strip("'")
            dst = [p for p in line.split("'")[0].split() if p in have and p != line.split("ssh")[0]]
            log.append(line)
            for h in have:
                if f" {h} 'mkdir" in line:
                    have[h].add(f)
            return 0, ""
        h = argv[-2]
        cmd = argv[-1]
        miss = [f for f in (F1, F2) if f in cmd and f not in have[h]]
        return 0, "\n".join(miss)
    return run, log


def test_missing_found_and_copied():
    have = {"epyc9": {F1, F2}, "epyc10": set(), "epyc8": {F1}}
    run, log = fake(have)
    hosts = list(have)
    miss = G.missing_by_host([F1, F2], hosts, run)
    assert miss == {"epyc9": [], "epyc10": sorted([F1, F2]), "epyc8": [F2]}
    out = []
    left = G.sync_missing({h: v for h, v in miss.items() if v}, hosts, run, out.append)
    assert left == {} and len(log) == 3
    assert all("--keep-old-files" in l for l in log) and any("ADOPT-GUARD copy" in l for l in out)
    assert have["epyc10"] == {F1, F2} and have["epyc8"] == {F1, F2}


def test_fail_closed_when_no_host_has_it_or_path_unsafe():
    have = {"epyc9": set(), "epyc10": set()}
    run, log = fake(have)
    miss = G.missing_by_host([F1], list(have), run)
    left = G.sync_missing(miss, list(have), run, lambda s: None)
    assert left == {"epyc9": [F1], "epyc10": [F1]} and not log
    left = G.sync_missing({"epyc9": ["/home/x/../etc/passwd"]}, ["epyc9", "epyc10"], run, lambda s: None)
    assert left == {"epyc9": ["/home/x/../etc/passwd"]}


def test_tree_gap_detected_and_filled():
    """KIT-OPS-6 item 9b: epyc7 tools/ with 1 file against 17,486 and no rtl/ at all"""
    stats = {"epyc9": {d: (n, "abc") for d, n in (("tools", 17486), ("rtl", 900), ("physical/die_plan", 300), ("physical/common_flow", 20))},
             "epyc7": {"tools": (1, "x"), "rtl": (0, ""), "physical/die_plan": (300, "abc"), "physical/common_flow": (20, "abc")}}
    gaps = G.tree_gaps(stats)
    assert gaps == {"epyc7": ["tools", "rtl"]}
    calls, out = [], []

    def run(argv, timeout=900):
        calls.append(argv[2]); return 0, ""
    left = G.tree_fill("/srv/opentallas-scratch2/claude/src", stats, gaps, run, out.append)
    assert left == {} and len(calls) == 2
    assert all("--keep-old-files" in c and "epyc9" in c and "epyc7" in c for c in calls)
    assert any("tree copy epyc9" in o and "1 -> 17486" in o for o in out)


def test_tree_stats_parse_and_missing_dir():
    def run(argv, timeout=900):
        cmd = argv[-1]
        return 0, ("17486 deadbeef0123" if "'/s/tools'" in cmd or "/s/tools" in cmd else "0 -")
    st = G.tree_stats("epyc7", "/s", run)
    assert st["tools"] == (17486, "deadbeef0123") and st["rtl"] == (0, "")


def test_plan_sha_mismatch_fails_loud_with_the_fix():
    cfg = {"dies": {"kv": {"plan": "/srv/opentallas-scratch2/claude/p/plan_c.json", "plan_sha256": "a" * 64}}}
    out = []

    def run(argv, timeout=900):
        return 0, "b" * 64 + "  plan_c.json\n"
    assert G.plan_sha_check(cfg, "kv", ["epyc7", "epyc9"], run, out.append) is False
    assert any("PLAN_SHA_MISMATCH kv epyc7" in o for o in out)
    assert any("FIX kv: set dies.kv.plan_sha256 to " + "b" * 64 in o for o in out)

    def ok(argv, timeout=900):
        return 0, "a" * 64 + "  plan_c.json\n"
    assert G.plan_sha_check(cfg, "kv", ["epyc7"], ok, lambda s: None) is True
    assert G.plan_sha_check({"dies": {"kv": {"plan": "/x"}}}, "kv", ["epyc7"], ok, lambda s: None) is True     # nothing declared


def test_published_tree_check_requires_the_marker_tree_and_hash(tmp_path):
    import json
    cfg = {"dies": {"x": {"src_manifest": "require", "src": "/srv/opentallas-scratch2/claude/kw45/src_x_pin_aaaaaaaaaaaa",
                          "src_manifest_hash": "h1"}, "y": {"src_manifest": "verify", "src": "/lane/run/b/src"}}}
    assert G.published_tree_check(cfg, "y", tmp_path) == []                    # not "require": not judged
    assert "no readable published-tree marker" in G.published_tree_check(cfg, "x", tmp_path)[0]   # a lane run copy has no marker
    (tmp_path / "tree_switch_x.json").write_text(json.dumps({"tree": "/lane/run/b/src", "src_manifest_sha": "h1"}))
    assert "not the published marker tree" in G.published_tree_check(cfg, "x", tmp_path)[0]
    (tmp_path / "tree_switch_x.json").write_text(json.dumps({"tree": cfg["dies"]["x"]["src"], "src_manifest_sha": "h2"}))
    assert "src_manifest_hash" in G.published_tree_check(cfg, "x", tmp_path)[0]
    (tmp_path / "tree_switch_x.json").write_text(json.dumps({"tree": cfg["dies"]["x"]["src"], "src_manifest_sha": "h1"}))
    assert G.published_tree_check(cfg, "x", tmp_path) == []
