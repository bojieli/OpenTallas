"""Full sink evidence is unavailable in a placement-only scoped bind."""
import json
from pathlib import Path


SINK_SIDECAR = "bind_sinks.json"


def reject_placement_probe(directory):
    directory = Path(directory)
    marker = directory / "BIND_PROBE_ONLY.json"
    if marker.exists():
        scope = json.loads(marker.read_text())
    else:
        report = directory / "bind_report.json"
        scope = json.loads(report.read_text()).get("probe_only") if report.exists() else None
    if SINK_SIDECAR in (scope or {}).get("omitted_sidecars", ()):
        raise ValueError(f"{directory}: placement-only bind omits full sink evidence; rebind without --omit-sink-sidecar")


def required_sink_sidecar(directory):
    reject_placement_probe(directory)
    path = Path(directory) / SINK_SIDECAR
    if not path.is_file():
        raise FileNotFoundError(f"full bind sink evidence is required: {path}")
    return path
