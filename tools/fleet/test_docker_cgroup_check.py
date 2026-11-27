import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import docker_cgroup_check as d


def test_judge_flags_missing_and_foreign_cgroup_parent():
    rows = [{"Name": "/a", "HostConfig": {"CgroupParent": "oth-ubuntu-1-2.service"}},
            {"Name": "/b", "HostConfig": {"CgroupParent": ""}},
            {"Name": "/c", "HostConfig": {"CgroupParent": "user.slice"}},
            {"Name": "/d", "HostConfig": {"CgroupParent": "system.slice/ot-run-x.service"}}]
    ok, bad = d.judge(rows)
    assert [n for n, _ in ok] == ["a", "d"]
    assert [n for n, _ in bad] == ["b", "c"]


def test_main_is_report_only_and_exits_zero(capsys):
    d.inspect_host = lambda h, run=None: [{"Name": "/x", "HostConfig": {}}]
    assert d.main(["--hosts", "h1"]) == 0
    assert "REPORT ONLY" in capsys.readouterr().out
