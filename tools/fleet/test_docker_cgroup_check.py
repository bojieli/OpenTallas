import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import docker_cgroup_check as d


def test_judge_flags_missing_label_or_cap():
    rows = [{"Name": "/a", "Config": {"Labels": {"ot.unit": "oth-u-1-2"}}, "HostConfig": {"Memory": 8 << 30}},
            {"Name": "/b", "Config": {"Labels": {}}, "HostConfig": {"Memory": 8 << 30}},
            {"Name": "/c", "Config": {"Labels": {"ot.unit": "oth-u-1-3"}}, "HostConfig": {"Memory": 0}},
            {"Name": "/d", "Config": {}, "HostConfig": {}}]
    ok, bad = d.judge(rows)
    assert [n for n, _ in ok] == ["a"]
    assert dict(bad) == {"b": "no ot.unit label", "c": "no memory cap", "d": "no ot.unit label, no memory cap"}


def test_main_is_report_only_and_exits_zero(capsys):
    d.inspect_host = lambda h, run=None: [{"Name": "/x", "Config": {}, "HostConfig": {}}]
    assert d.main(["--hosts", "h1"]) == 0
    out = capsys.readouterr().out
    assert "REPORT ONLY" in out and "no ot.unit label" in out
