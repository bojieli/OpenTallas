import json

import pytest

from bind_sink_sidecar import required_sink_sidecar


def test_legacy_and_missing_sink_evidence(tmp_path):
    path = tmp_path / "bind_sinks.json"
    with pytest.raises(FileNotFoundError, match="full bind sink evidence"):
        required_sink_sidecar(tmp_path)
    path.write_text("{}")
    assert required_sink_sidecar(tmp_path) == path


@pytest.mark.parametrize("receipt", ["BIND_PROBE_ONLY.json", "bind_report.json"])
def test_placement_probe_refuses_even_a_copied_sink_sidecar(tmp_path, receipt):
    (tmp_path / "bind_sinks.json").write_text("{}")
    scope = {"emitted": ["ta"], "omitted_sidecars": ["bind_sinks.json"]}
    payload = {"probe_only": scope} if receipt == "bind_report.json" else scope
    (tmp_path / receipt).write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="placement-only bind"):
        required_sink_sidecar(tmp_path)
