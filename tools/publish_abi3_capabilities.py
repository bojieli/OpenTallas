#!/usr/bin/env python3
"""Publish the capability files from the profiles that define them.

A capability had two sources of truth and they came apart. The campaign runner
reads ``configs/hardware/abi3_capability/*.json``; the backends, the tests and
the checkers build the same capability in code. Adopting amendment A8's frozen
RMSNorm contract name in the DeepSeek exporter changed the derived contract
union, which changed the code-built profile -- and moved Qwen's *deployment*
digest, because a deployment binds the capability it was admitted against, while
the JSON on disk stayed where it was. The agent making the change had
deliberately not edited the JSON, precisely to avoid moving that digest. It
moved anyway, through the other source.

Nothing about that is subtle once there are two of a thing. So there is now one:
the profile in code is the definition, this tool publishes it, and ``--check``
fails when the published file has drifted. That is the same discipline
``runtime.sim.device.loop_trip_count`` enforces for the trip-count formula, for
the same reason -- two restatements of one rule is how two of them diverge.

The published file stays the campaign runner's input. It is an artifact, not a
second opinion.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json  # noqa: E402

CONFIG_ROOT = REPO / "configs" / "hardware" / "abi3_capability"

#: Published file stem -> the profile that defines it.
PUBLISHED: dict[str, tuple[str, str]] = {
    "hbm_sram_single_chip": ("compiler.backends.hbm_sram.capability", "single-chip"),
    "hbm_sram_cluster_32": ("compiler.backends.hbm_sram.capability", "cluster-32"),
    # The two ROM profiles had the same two sources of truth this tool exists
    # to remove, and were simply not listed here: the file on disk and
    # ``qwen3_rom_capability`` / ``deepseek_v4_rom_capability`` happened to
    # agree, with nothing checking that they did.  Found while adding
    # amendments A22 and A23, which change all four.
    "rom_qwen3": ("compiler.backends.rom.qwen3", "rom-qwen3"),
    "rom_deepseek_v4": ("compiler.backends.rom.deepseek_v4", "rom-deepseek-v4"),
    "rom_deepseek_v4_array_32": (
        "compiler.backends.rom.deepseek_v4_array",
        "rom-deepseek-v4-array-32",
    ),
}


def _profile(module_name: str, key: str):
    import importlib

    profiles = importlib.import_module(module_name).PROFILES
    capability = profiles[key]
    return capability() if callable(capability) else capability


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit non-zero if any published file has drifted",
    )
    args = parser.parse_args()

    drifted: list[str] = []
    for stem, (module_name, key) in sorted(PUBLISHED.items()):
        capability = _profile(module_name, key)
        path = CONFIG_ROOT / f"{stem}.json"
        published = canonical_json(json.loads(json.dumps(capability.to_dict())))
        current = path.read_bytes() if path.exists() else b""
        if current == published:
            print(f"{stem}: current ({capability.digest[:16]})")
            continue
        if args.check:
            on_disk = "absent"
            if current:
                from runtime.abi3.capability import Capability, digest_of

                body = json.loads(current)
                try:
                    on_disk = Capability.from_dict(body).digest[:16]
                except ValueError as exc:
                    # A published file that no longer validates is exactly the
                    # drift this tool reports; saying so beats raising out of
                    # the reporting path.
                    on_disk = f"{digest_of(body)[:16]} (invalid: {exc})"
            print(
                f"{stem}: DRIFTED -- profile is {capability.digest[:16]}, "
                f"published file is {on_disk}"
            )
            drifted.append(stem)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(published)
        print(f"{stem}: published ({capability.digest[:16]})")

    if drifted:
        print(
            f"\n{len(drifted)} capability file(s) drifted from the profile that "
            "defines them. Run this tool without --check to republish, and note "
            "that doing so changes the deployment digest of every deployment "
            "admitted against them -- which is correct, and is why it must be a "
            "deliberate step rather than a silent one."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
