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
            f = "/" + line.split("tar -C / -cf - ")[1].split()[0].strip("'")
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
