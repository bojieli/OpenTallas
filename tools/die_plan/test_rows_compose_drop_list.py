import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose_drop_guard as CDG  # noqa: E402
import rows_compose_drop_list as R  # noqa: E402


def _plan(relays, ins, tap=None):
    return {"clock": {"tap_offset": {"per_port_ps": {"p": dict(tap or {})}}},
            "partition_types": {"t": {"clock": {"reset_tree_anchor": {"inputs": ins, "relays": relays}}}}}


OLD = _plan({"rst_rl_1": {"depth": 1}, "rst_rl_2": {"depth": 2}}, {"sink_bins": "a", "taps": "x"}, {"clk_t1": 1, "clk_t2": 2})
NEW = _plan({"rst_rl_3": {"depth": 1}}, {"sink_bins": "b", "taps": "x"}, {"clk_t1": 1})


def test_reanchored_relays_named_with_evidence_other_drops_not():
    text, named, unnamed = CDG.emit_drop_list(OLD, NEW)
    assert named == ["partition_types.t.clock.reset_tree_anchor.relays.rst_rl_1", "partition_types.t.clock.reset_tree_anchor.relays.rst_rl_2"]
    assert unnamed == ["clock.tap_offset.per_port_ps.p.clk_t2"]
    assert "re-anchored: inputs sink_bins changed" in text
    same = _plan({"rst_rl_3": {"depth": 1}}, {"sink_bins": "a", "taps": "x"})
    assert CDG.emit_drop_list(OLD, same)[1] == []                     # same inputs: a relay drop is a loss


def test_row_writes_list_and_pre_reads_it(tmp_path):
    (tmp_path / "base.json").write_text(json.dumps(OLD))
    (tmp_path / "plan.json").write_text(json.dumps(NEW))
    args = [str(tmp_path / "plan.json"), str(tmp_path / "out.json"), str(tmp_path / "rep.json"), "--baseline", str(tmp_path / "base.json")]
    assert R.main(args) == 1 and not (tmp_path / "compose_drop_list.txt").exists()
    assert R.main(args + ["--intend", "clock.tap_offset.per_port_ps.p.clk_t2 # 2 -> 1 taps"]) == 0
    lst = (tmp_path / "compose_drop_list.txt").read_text()
    assert "clk_t2  # 2 -> 1 taps" in lst and "re-anchored" in lst
    assert CDG.findings_for_pre(OLD, NEW, level="FAIL", plan_path=str(tmp_path / "out.json")) == []
    assert CDG.findings_for_pre(OLD, NEW, level="FAIL", plan_path=str(tmp_path / "plan.json")) == []   # same plan dir
    assert CDG.findings_for_pre(OLD, NEW, level="FAIL")
