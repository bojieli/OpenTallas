"""Load versioned model and architecture profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import ArchitectureProfile, ModelProfile


def load_architectures(path: str | Path) -> tuple[list[ArchitectureProfile], ArchitectureProfile, dict[str, Any]]:
    source = Path(path)
    with source.open(encoding="utf-8") as handle:
        data = json.load(handle)
    gpus = [ArchitectureProfile(**entry) for entry in data["gpu_architectures"]]
    rom = ArchitectureProfile(**data["rom_architecture"])
    metadata = {key: value for key, value in data.items() if key not in {"gpu_architectures", "rom_architecture"}}
    return gpus, rom, metadata


def load_model_dir(path: str | Path) -> list[ModelProfile]:
    return [ModelProfile.load(item) for item in sorted(Path(path).glob("*.json"))]
