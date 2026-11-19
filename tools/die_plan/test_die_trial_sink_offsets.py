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
