"""The raw reading of the semantic record equals the decoded one.

``runtime/abi3/semantic_record.py`` exists so an RTL collector has a checked
specification to implement.  The engines that consume the 128-word record --
``ot_a3_hc_pre_t1_descriptor_rne`` and ``ot_a3_vector_mhc_pre_tile_scheduler`` --
are fed it as one bundle, and nothing in the device assembles it: the bridge holds
the operator, numeric payload and resolved views but never sees the SCHEDULE
descriptor, which the microsequencer decodes in its own state, and the views arrive
later still from the resolver bank.  A collector has to latch each as the sequencer
walks past it, and what it has to work from is 192 raw bytes per descriptor.

So there are two readings of one record: ``config_words`` reads decoded Python
descriptors, and ``record_from_raw`` reads bytes at ABI offsets.  This asserts they
agree word for word on both shipped stores, which is what makes either usable as
the other's golden.  Without it a transcription error in the byte offsets would
show up only as an RTL bench failure with nothing to attribute it to.
"""

from __future__ import annotations

import json

import pytest

from tools import build_a3_mhc_pre_tile_vectors as tile_vectors
from runtime.abi3.semantic_record import CONFIG_WORDS, record_from_raw

ROLES = (
    "operator", "counter", "numeric", "schedule", "wait",
    "input0", "input1", "input2", "input3", "output0", "output1",
)


def profiles():
    manifest = json.loads(tile_vectors.DEPLOYMENT_MANIFEST.read_bytes())
    descriptors = tile_vectors.read_hex(tile_vectors.DESCRIPTOR_IMAGE)
    programs = tile_vectors.read_hex(tile_vectors.PROGRAM_IMAGE)
    bases = tile_vectors.deployment_bases(manifest)
    for target in tile_vectors.TARGETS:
        yield target, tile_vectors.selected_profile(
            target, manifest, descriptors, programs, bases
        )


@pytest.mark.parametrize("active_tokens", (1,))
def test_raw_reading_equals_the_decoded_reading(active_tokens: int) -> None:
    seen = 0
    for target, profile in profiles():
        golden = tile_vectors.config_words(profile, active_tokens)
        assert len(golden) == CONFIG_WORDS
        instruction = profile["instruction"]
        mine = record_from_raw(
            profile=int(target["profile"]),
            active_tokens=active_tokens,
            program_counter=int(target["pc"]),
            instruction={
                "flags": int(instruction.flags),
                "descriptor_id": int(instruction.descriptor_id),
                "wait_set_id": int(instruction.wait_set_id),
                "signal_event_id": int(instruction.signal_event_id),
                "control_id": int(instruction.control_id),
                "source_operation_id": int(instruction.source_operation_id),
            },
            raw={role: profile["records"][role] for role in ROLES},
        )
        assert mine == golden, (
            f"{target['key']}: the raw reading differs at words "
            f"{[i for i, (g, m) in enumerate(zip(golden, mine)) if g != m]}"
        )
        seen += 1
    # Both shipped stores, or the parametrisation has silently stopped covering one.
    assert seen == 2


def test_the_record_names_every_descriptor_it_needs() -> None:
    """A missing role is refused by name, not read as zero."""
    for target, profile in profiles():
        raw = {role: profile["records"][role] for role in ROLES}
        raw.pop("schedule")
        with pytest.raises(Exception) as caught:
            record_from_raw(
                profile=int(target["profile"]),
                active_tokens=1,
                program_counter=int(target["pc"]),
                instruction={
                    "flags": 0, "descriptor_id": 0, "wait_set_id": 0,
                    "signal_event_id": 0, "control_id": 0,
                    "source_operation_id": 0,
                },
                raw=raw,
            )
        assert "schedule" in str(caught.value)
        break
