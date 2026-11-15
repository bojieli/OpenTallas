"""WF-1 11-14: make Error 241 / earlyoom-matched SIGTERM is an infra-oom kill, resubmitted without a --mem raise."""
import autopilot as A


def test_error_241_matches_the_oom_probe_pattern():
    import re
    pat = re.compile(A.PROBE_CLASSIFY and r"\] Error 24[17]\b")
    assert pat.search("make[1]: *** [Makefile:589: do-5_2_route] Error 241")
    assert "Error 24[17]" in open(A.__file__).read()


def test_is_earlyoom_kill():
    assert A.is_earlyoom_kill("make[1]: *** [Makefile:589: do-5_2_route] Error 241")
    assert A.is_earlyoom_kill("earlyoom SIGTERM on epyc9 within 60 s of the exit")
    assert not A.is_earlyoom_kill("Error 137 Killed")


def test_classify_error_241_is_infra_oom():
    c = {"oom": "] Error 241"}
    cls, kind, why = A.classify(c, {"exit": 2})
    assert (cls, kind) == ("CRASH", "infra-oom") and "241" in why


def test_earlyoom_kill_near_uses_journal_count():
    calls = []

    def probe(argv, timeout=0):
        calls.append(argv)
        return 0, "2\n", ""
    assert A.earlyoom_kill_near("epyc9", 1_000_000, probe=probe)
    assert "--since @999940" in calls[0][-1] and "--until @1000060" in calls[0][-1]
    assert not A.earlyoom_kill_near("epyc9", 1_000_000, probe=lambda a, timeout=0: (0, "0\n", ""))
    assert not A.earlyoom_kill_near("epyc9", 1_000_000, probe=lambda a, timeout=0: (255, "", ""))
    assert not A.earlyoom_kill_near("", 1_000_000, probe=probe)
