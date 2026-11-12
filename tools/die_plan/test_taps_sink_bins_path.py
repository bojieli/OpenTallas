"""DIE-KV-99 11-12: taps.sink_sites with clock.sink_bins_file resolved against the plan folder (81f2a99558 used
Path without importing it, so G0 / bind crashed on every plan with a sink_bins_file, e.g. KV sys_SD_v1)."""
import json
import os
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taps  # noqa: E402


def test_sink_bins_file_resolves_under_plan_dir():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "sink_bins"))
        json.dump({"bin_um": 10, "bins": [[5.0, 5.0, 3], [15.0, 5.0, 0]]}, open(os.path.join(d, "sink_bins", "t.json"), "w"))
        P = types.SimpleNamespace(types={"t": {"clock": {"sink_bins_file": "sink_bins/t.json"}}},
                                  path=os.path.join(d, "die_plan.json"))
        assert taps.sink_sites(P, "t", control=False) == [(5.0, 5.0, 3.0)]
