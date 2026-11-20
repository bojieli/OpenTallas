"""FLEET-WATCH-1015: UNSIGNABLE rule of the no-progress watchdog (job > 3 h, measured post-CTS setup < -300 ps), report hour first, cancel only by ot-run --cancel <exact unit>."""
import json, os, sys, types
sys.path.insert(0, os.path.dirname(__file__))
import noprog_watchdog as nw

NOW = 1_000_000_000.0


def cts(d, ws, mtime):
    p = d / "run/logs/asap7/dp_x/base/4_1_cts.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"cts__timing__setup__ws": ws, "cts__timing__hold__ws": -9999.0}))
    os.utime(p, (mtime, mtime))
    return p


def test_measured_setup_reads_only_the_file_this_job_wrote(tmp_path):
    cts(tmp_path, -1550.85, NOW - 100)
    assert nw.measured_setup([str(tmp_path)], NOW - 3600)[0] == -1550.85
    assert nw.measured_setup([str(tmp_path)], NOW + 5000) is None            # written before this container started: an earlier attempt
    assert nw.measured_setup([str(tmp_path / "nothing"), None, ""], 0) is None
    (tmp_path / "run/logs/asap7/dp_x/base/4_1_cts.json").write_text("{not json")
    assert nw.measured_setup([str(tmp_path)], 0) is None
    (tmp_path / "run/logs/asap7/dp_x/base/4_1_cts.json").write_text(json.dumps({"cts__timing__hold__ws": -500.0}))
    assert nw.measured_setup([str(tmp_path)], 0) is None                      # hold-only data is not a setup measurement


def ev(setup, age=12.0, ident="dpkit-col_h9_r2__t1-1", prio="", kind="other"):
    return nw.unsignable_evidence(ident, prio, kind, age, None if setup is None else (setup, "/k/4_1_cts.json"))


def test_the_rule_fires_only_below_minus_300_and_after_3_h():
    assert "-301.00 ps" in ev(-301.0) and "-1550.85" in ev(-1550.85)
    for s in (-300.0, -299.0, -150.0, -42.0, 10.0, None):                     # between -42 and -300, at the line, positive, unmeasured
        assert ev(s) is None, s
    assert ev(-500.0, age=3.0) is None and ev(-500.0, age=2.0) is None and ev(-500.0, age=3.1)


def test_never_proofs_ecos_plan_jobs_lec_or_hbm():
    assert ev(-900, prio="plan") is None and ev(-900, prio="proof") is None and ev(-900, kind="lec") is None
    assert ev(-900, ident="dpkit-x-eco_r2-5") is None and ev(-900, ident="/srv/a/eco/gen/t1") is None
    assert ev(-900, ident="/srv/a/coll_core_proof_pkw2b/gen/t1") is None
    assert ev(-900, ident="/srv/a/runs/hbm/kit-wave/hbm/p/items/t1") is None
    assert ev(-900, ident="dpkit-second_core-7") is not None                    # 'eco' inside a word is not an ECO


def row(unit="oth-ubuntu-1-2", host="epyc9", key="c1|/k1", verdict=nw.UNSIGNABLE):
    return {"unit": unit, "host": host, "key": key, "verdict": verdict, "type": "t1", "kit": "/s/runs/s81/kit-wave/s81/3fa87b/items/t1/gen/t1", "why": "4_1_cts.json cts__timing__setup__ws -700.00 ps",
            "gb": 48.0, "setup_ps": -700.0, "age_h": 12.0}


def coord(tmp_path, monkeypatch):
    (tmp_path / "bin").mkdir(); (tmp_path / "lanes").mkdir()
    (tmp_path / "bin/post.sh").write_text("#!/bin/bash\necho \"$1|$2\" >> " + str(tmp_path / "posted") + "\n")
    monkeypatch.setattr(nw, "COORD", str(tmp_path)); monkeypatch.delenv("NOPROG_UNSIGNABLE_MODE", raising=False)


def test_report_hour_then_cancel_by_exact_unit(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    calls, seen = [], {}
    cancel = lambda u: (calls.append(u), (0, "containers stopped: dpkit-t1-1"))[1]
    mode, cand, done = nw.unsignable_pass([row()], seen, NOW, cancel=cancel)
    assert mode == "report" and len(cand) == 1 and done == [] and calls == []
    assert (tmp_path / "posted").read_text().startswith("FLEET-WATCH-1015|UNSIGNABLE watchdog (report mode") and "epyc9 t1 -700 ps" in (tmp_path / "posted").read_text()
    mode, _c, done = nw.unsignable_pass([row()], seen, NOW + 1800, cancel=cancel)                  # half an hour: still report only
    assert mode == "report" and calls == []
    assert (tmp_path / "posted").read_text().count("\n") == 1                                      # the list is not re-posted every tick
    mode, _c, done = nw.unsignable_pass([row()], seen, NOW + 3601, cancel=cancel)
    assert calls == ["oth-ubuntu-1-2"] and done[0]["unit"] == "oth-ubuntu-1-2"
    tsv = (tmp_path / "lanes/CANCEL-UNSIGNABLE-1120.tsv").read_text().splitlines()
    assert len(tsv) == 1 and tsv[0].split("\t")[:3] == ["oth-ubuntu-1-2", "epyc9", "t1"] and "s81 3fa87b" in tsv[0] and "ot-run --cancel oth-ubuntu-1-2 rc=0" in tsv[0] and tsv[0].split("\t")[5] == "48.0"


def test_act_mode_skips_siblings_young_listings_and_unitless_rows(tmp_path, monkeypatch):
    coord(tmp_path, monkeypatch)
    monkeypatch.setenv("NOPROG_UNSIGNABLE_MODE", "act")
    calls = []
    cancel = lambda u: (calls.append(u), (0, "ok"))[1]
    seen = {"unsig_listed": {"epyc9|c1|/k1": NOW - 2000, "epyc9|c3|/k3": NOW - 2000}}
    rows = [row(), row(unit="oth-ubuntu-9-9", key="c2|/k2", verdict="PROGRESS"), row(unit="oth-ubuntu-9-9", key="c2b|/k2b"),     # a healthy sibling blocks the unit
            row(unit="oth-ubuntu-5-5", key="young|/k5"),                                                                       # listed this tick
            row(unit=None, key="c3|/k3")]                                                                                      # no scope: nothing to cancel by unit
    mode, _c, done = nw.unsignable_pass(rows, seen, NOW, cancel=cancel)
    assert mode == "act" and calls == ["oth-ubuntu-1-2"] and len(done) == 1


def test_cancel_goes_through_ot_run_cancel_with_the_exact_unit():
    seen = []
    def run(argv, **k):
        seen.append(argv); return types.SimpleNamespace(returncode=0, stdout="ot-run --cancel: epyc9: containers stopped: x\n", stderr="")
    assert nw.ot_run_cancel("oth-ubuntu-1-2", run=run) == (0, "ot-run --cancel: epyc9: containers stopped: x")
    assert seen[0][1:] == ["--cancel", "oth-ubuntu-1-2"] and seen[0][0].endswith("ot-run")


def test_unsignable_is_not_a_host_cancel_verdict():
    assert nw.UNSIGNABLE not in nw.BAD_VERDICTS            # a host scan never cancels it; only the hub, after the report hour
