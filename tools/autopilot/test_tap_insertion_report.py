"""WAVE-FLOW-R2 11-17 (COORD lever 6): the OT_TAP_INSERTION collector and the per-die summary failure_breakdown prints."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tap_insertion_report as R

LOG = """noise
OT_TAP_INSERTION tap=clk_t0 sinks=40 ins_ps=212.5 skew_ps=62.5
OT_TAP_INSERTION tap=clk_t1 sinks=1700 ins_ps=260.0 skew_ps=160.0
OT_TAP_INSERTION total taps=2
"""


def test_parse_ignores_noise_and_the_total_line():
    assert R.parse_lines(LOG) == [("clk_t0", 40, 212.5, 62.5), ("clk_t1", 1700, 260.0, 160.0)]
    assert R.parse_lines("OT_TAP_INSERTION WARN: not printed: boom") == []


def test_kits_from_state_takes_the_newest_job_per_type():
    st = {"jobs": {"a": {"die": "kv", "type": "t1", "kit": "epyc10:/k/old", "finished": 1}, "b": {"die": "kv", "type": "t1", "kit": "epyc9:/k/new", "finished": 5},
                   "c": {"die": "qc", "type": "t2", "kit": "epyc8:/k/c", "updated": 3}, "d": {"die": "qc", "type": "t3", "kit": "nohost"}}}
    assert R.kits_from_state(st) == [("kv", "t1", "epyc9", "/k/new"), ("qc", "t2", "epyc8", "/k/c")]


def test_scan_and_summary(tmp_path):
    seen = []

    def run(host, script):
        seen.append(host)
        return f"@@KIT /k/new\n{LOG.splitlines()[1]}\n{LOG.splitlines()[2]}\n"
    got = R.scan_host("epyc9", ["/k/new", "/k/none"], run=run)
    assert list(got) == ["/k/new"] and "clk_t1" in got["/k/new"]
    state = {"jobs": {"b": {"die": "kv", "type": "t1", "kit": "epyc9:/k/new", "finished": 5}}}
    out = tmp_path / "ti.json"
    doc = R.update(state, out, scan=lambda host, kits: got)
    s = doc["dies"]["kv"]
    assert s["taps"] == 2 and s["oversized_taps"] == 1 and s["ins_ps_max"] == 260.0 and s["skew_ps_max"] == 160.0 and s["oversized_skew_ps_max"] == 160.0
    assert json.loads(out.read_text())["dies"]["kv"]["worst"][0]["tap"] == "clk_t1"
    ln = R.lines(doc)[0]
    assert ln.startswith("TAP-INSERTION kv: 2 taps in 1 types, 1 over 1650 sinks; insertion max 260 ps")


def test_scan_command_reads_only_the_newest_cts_log():
    cmds = []
    R.scan_host("epyc9", ["/k/a"], run=lambda host, script: cmds.append(script) or "")
    assert "for k in /k/a;" in cmds[0] and "ls -t $k/run/logs/asap7/*/base/4_1_cts.log" in cmds[0] and "head -1" in cmds[0] and "grep -h '^OT_TAP_INSERTION tap='" in cmds[0]
