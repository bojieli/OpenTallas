"""Load versioned model and architecture profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import ArchitectureProfile, ModelProfile


def load_architecture_envelopes(
    path: str | Path,
) -> tuple[list[ArchitectureProfile], list[ArchitectureProfile], dict[str, Any]]:
    """Load every GPU and wafer envelope from a study configuration.

    Legacy configurations contain one ``rom_architecture``.  Evidence-baselined
    studies use ``wafer_architectures`` (or ``rom_architectures``) so
    conservative/central/aggressive cases cannot be collapsed into one false-
    precision midpoint.
    """

    source = Path(path)
    with source.open(encoding="utf-8") as handle:
        data = json.load(handle)
    gpus = [
        ArchitectureProfile.from_dict(entry)
        for entry in data.get("gpu_architectures", ())
    ]
    if "wafer_architectures" in data:
        wafer_entries = data["wafer_architectures"]
    elif "rom_architectures" in data:
        wafer_entries = data["rom_architectures"]
    elif "rom_architecture" in data:
        wafer_entries = [data["rom_architecture"]]
    else:
        wafer_entries = []
    wafers = [ArchitectureProfile.from_dict(entry) for entry in wafer_entries]
    excluded = {
        "gpu_architectures",
        "wafer_architectures",
        "rom_architectures",
        "rom_architecture",
    }
    metadata = {key: value for key, value in data.items() if key not in excluded}
    return gpus, wafers, metadata


def load_architectures(path: str | Path) -> tuple[list[ArchitectureProfile], ArchitectureProfile, dict[str, Any]]:
    gpus, wafers, metadata = load_architecture_envelopes(path)
    if len(wafers) != 1:
        raise ValueError(
            f"load_architectures requires exactly one wafer profile, found {len(wafers)}; "
            "use load_architecture_envelopes for bounded studies"
        )
    return gpus, wafers[0], metadata


def load_model_dir(path: str | Path) -> list[ModelProfile]:
    return [ModelProfile.load(item) for item in sorted(Path(path).glob("*.json"))]
