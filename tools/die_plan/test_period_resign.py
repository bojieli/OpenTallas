"""SIGN-PERIOD (OWNER 2026-11-20 (1)): sign the same routed DB at the smallest period <= 1000 ps where TT setup >= -42 ps; hold re-checked;
the 833 result kept; a record timed above 833 ps counts only with a matching signed_period_ps."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import period_resign as PR  # noqa: E402
import signoff_profile as SP  # noqa: E402

SDC = """create_clock -name clk -period 833.0000 [get_ports {clk clk_t1}]
create_clock -name vclk -period 833.0000
create_clock -name h -period 833 -waveform {0 416.5} [get_ports x]
set p 833
create_clock -name q -period $p [get_ports q]
set_input_delay -max 559.7200 -clock vclk [get_ports a]
set_output_delay -max 166.6000 -clock vclk [get_ports b]
set_clock_uncertainty 25.0000 -hold [all_clocks]
"""


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for k in ("OT_SIGNOFF_PROFILE", "OT_DIE_PERIOD_PS", "OT_DIE_PERIOD_PS_S81"):
        monkeypatch.delenv(k, raising=False)


def rec(tt, ff=2.0, drc=0, period=833.0, sp=None, sdc="/x.sdc", base="/b"):
    r = dict(name="t1", verdict="NOT SIGNED", inputs=dict(base=base, kit="/k", sdc=sdc),
             checks=dict(drc=dict(count=drc), setup_tt=dict(wns_ps=tt), hold_ff=dict(wns_ps=ff)),
             corners=dict(tt=dict(periods=dict(clk=period, vclk=period, fclk_out=0.0)),
                          ff=dict(done=True, rc=0, periods=dict(clk=period), std_min_start=dict(err=0, trunc=0, core_wns=ff, core_n=0 if ff >= 0 else 3))))
    if sp is not None:
        r["signed_period_ps"] = sp
    return r


def test_sdc_scales_only_clock_periods():
    t, n = PR.scaled_sdc(SDC, 900)
    assert n == 4
    assert "create_clock -name clk -period 900.0000" in t and "create_clock -name vclk -period 900.0000" in t
    assert "-waveform {0.0000 450.0000}" in t and "set p 900.0000" in t and "-period $p" in t
    assert "set_input_delay -max 559.7200" in t and "set_output_delay -max 166.6000" in t and "25.0000 -hold" in t


def test_first_and_next_period_on_the_grid():
    assert PR.first_period(-30) == 833.0
    assert PR.first_period(-100) == 895.0            # 833 - 42 + 100 = 891 -> 895
    assert PR.first_period(-209) == 1000.0
    assert PR.first_period(-210) == 1005.0
    assert PR.next_period(895, -60) == 915.0          # deficit 18 -> 913 -> 915
    assert PR.next_period(895, -43) == 900.0          # at least one step


def test_check_verdicts():
    assert PR.check(rec(-100))["verdict"] == "ELIGIBLE" and PR.check(rec(-100))["first_period_ps"] == 895.0
    assert PR.check(rec(-10))["verdict"] == "SIGNED_AT_833"
    assert PR.check(rec(-100, ff=-3))["verdict"] == "HOLD_FIRST"
    assert PR.check(rec(-100, drc=4))["verdict"] == "NOT_ELIGIBLE"
    assert PR.check(rec(-300))["verdict"] == "OVER_1000"
    assert PR.check(rec(-20, period=900, sp=900))["verdict"] == "NOT_ELIGIBLE"


def test_profile_period_gate():
    assert SP.judge(rec(-30, period=900))["verdict"] == "NOT SIGNED"                    # >833 clock without signed_period_ps
    assert "without signed_period_ps" in SP.judge(rec(-30, period=900))["reasons"][0]
    j = SP.judge(rec(-30, period=900, sp=900))
    assert j["verdict"] == "SIGNED" and j["signed_period_ps"] == 900 and j["achieved_period_ps"] == 900
    assert SP.judge(rec(-30, period=905, sp=900))["verdict"] == "NOT SIGNED"            # declared != measured
    assert SP.judge(rec(-30, period=1100, sp=1100))["verdict"] == "NOT SIGNED"          # above the 1000 cap
    assert SP.judge(rec(-50, period=900, sp=900))["verdict"] == "NOT SIGNED"            # -42 at the signed period
    assert SP.judge(rec(-30))["signed_period_ps"] == 833.0
    assert SP.judge(rec(10, ff=-1, period=900, sp=900))["verdict"] == "NOT SIGNED"      # hold unchanged


def test_die_period_helpers(tmp_path):
    assert SP.die_period_from_types([None, 900, 955]) == 955 and SP.die_period_from_types([]) == 833.0
    f = tmp_path / "DIE-PERIOD.tsv"
    f.write_text("# x\ns81\t935\tcol_a\t\nqwen_compute\t833\t\t\n")
    assert SP.signed_die_period_ps("s81", f) == 935 and SP.signed_die_period_ps("qc", f) == 833 and SP.signed_die_period_ps("kv", f) == 833


def fake_runner(results):
    """signoff.py stand-in: writes a record at the trial period with the TT WNS of `results`"""
    def run(cmd, log):
        out = Path(cmd[cmd.index("--out") + 1])
        sdc = Path(cmd[cmd.index("--sdc") + 1]).read_text()
        import re
        p = float(re.search(r"-name clk -period ([\d.]+)", sdc).group(1))
        out.mkdir(parents=True, exist_ok=True)
        (out / "signoff.json").write_text(json.dumps(rec(results[p], period=p)))
        Path(log).write_text("ok\n")
        return 0
    return run


def test_run_searches_and_writes_the_period_record(tmp_path):
    unit = tmp_path / "kit"
    (unit / "signoff").mkdir(parents=True)
    (unit / "constraint.sdc").write_text(SDC)
    r833 = rec(-100, sdc=str(unit / "constraint.sdc"))
    (unit / "signoff" / "signoff.json").write_text(json.dumps(r833))
    a = type("A", (), dict(signoff=str(unit / "signoff" / "signoff.json"), out=None, step=5, max=1000, image=None, dry=False))
    # last resort (COORD 11-20): no failed 833 ECO yet -> ECO_FIRST, nothing timed
    assert PR.run(a, runner=lambda *x: pytest.fail("timed before the 833 ECO")) == 3
    assert json.loads((unit / "signoff_period" / "period_resign.json").read_text())["verdict"] == "ECO_FIRST"
    (unit / "eco_1").mkdir()
    (unit / "eco_1" / "eco_loop.json").write_text(json.dumps(dict(verdict="EXHAUSTED")))
    # half-cycle paths: 895 gives only -60, 915 passes
    rc = PR.run(a, runner=fake_runner({895.0: -60.0, 915.0: -38.0}))
    assert rc == 0
    d = unit / "signoff_period"
    fin = json.loads((d / "signoff.json").read_text())
    assert fin["signed_period_ps"] == 915.0 and fin["verdict"] == "SIGNED"
    assert fin["at_833"]["tt_wns_ps"] == -100 and fin["at_833"]["sha256"]
    assert [x["period_ps"] for x in fin["period_search"]] == [895.0, 915.0]
    assert not (d / "trial_p895" / "signoff.json").exists() and (d / "trial_p895" / "sta_p895.json").exists()
    assert json.loads((d / "period_resign.json").read_text())["verdict"] == "SIGNED_AT_PERIOD"
    assert SP.judge(fin)["verdict"] == "SIGNED"
    assert fin["period_eco_evidence"]["evidence"][0][1] == "EXHAUSTED"


def test_a_passing_833_eco_blocks_the_relaxed_period(tmp_path):
    unit = tmp_path / "kit"
    (unit / "signoff").mkdir(parents=True)
    for n, v in (("eco_1", "EXHAUSTED"), ("eco_2", "PASS")):
        (unit / n).mkdir()
        (unit / n / "eco_loop.json").write_text(json.dumps(dict(verdict=v)))
    r = rec(-100)
    r["inputs"]["kit"] = str(unit)
    assert PR.eco_evidence(unit / "signoff" / "signoff.json", r) == []


def test_run_stops_above_1000(tmp_path):
    unit = tmp_path / "kit"
    (unit / "signoff").mkdir(parents=True)
    (unit / "constraint.sdc").write_text(SDC)
    (unit / "signoff" / "signoff.json").write_text(json.dumps(rec(-200, sdc=str(unit / "constraint.sdc"))))
    a = type("A", (), dict(signoff=str(unit / "signoff" / "signoff.json"), out=None, step=5, max=1000, image=None, dry=False,
                           no_eco_evidence=True))
    rc = PR.run(a, runner=fake_runner({995.0: -60.0, 1000.0: -50.0}))
    assert rc == 1 and not (unit / "signoff_period" / "signoff.json").exists()
    assert json.loads((unit / "signoff_period" / "period_resign.json").read_text())["verdict"] == "OVER_1000"


def test_max_above_1000_refused(tmp_path):
    with pytest.raises(SystemExit):
        PR.main(["run", "--signoff", str(tmp_path / "x.json"), "--max", "1100"])
