"""DIE-CORETAP-1119: per-port core tap DME sink offsets (die_trial --region-dme-sink-offsets)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as DT  # noqa: E402


def test_sink_offsets_model_keys_ratio_and_unknown_part(tmp_path):
    P = SimpleNamespace(parts={"pc_ES_2": {}, "a": {}})
    f = tmp_path / "o.json"
    f.write_text(json.dumps({"offsets_ps": {"t_pc_ES_2__clk_c3": 68.0, "pc_ES_2/clk_c4": -57.0}}))
    assert DT.sink_offsets_model(f, P, 2.0) == {("pc_ES_2", "clk_c3"): 34.0, ("pc_ES_2", "clk_c4"): -28.5}
    f.write_text(json.dumps({"t_nope__clk_c0": 1.0}))
    with pytest.raises(ValueError, match="not in the plan"):
        DT.sink_offsets_model(f, P)


def test_leaf_sink_is_ps_with_merge_early_sinks():
    # FABLE-PD-KV-0845: the tap leg (um) was added to the ps sink delay; with early merge sinks it is tap_wire_ps
    assert DT.leaf_sink_ps(136.6, 150.0, False, True) == pytest.approx(DT.tap_wire_ps(136.6))
    assert DT.leaf_sink_ps(136.6, 150.0, False, True) < 136.6 / 2
    assert DT.leaf_sink_ps(136.6, 150.0, False, False) == 136.6          # stock delay tree unchanged (reproducible)
    assert DT.leaf_sink_ps(136.6, None, False, True) == 136.6            # length-mode DME: S is um throughout
