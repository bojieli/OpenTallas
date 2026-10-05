"""Wire and semantic admission tests for ABI 3.0 request-symbol records."""

from __future__ import annotations

from dataclasses import replace

import pytest

from runtime.abi3.constants import DESCRIPTOR_ALIGNMENT
from runtime.abi3.crc import record_crc
from runtime.abi3.descriptors import Phase, Symbol
from runtime.abi3.fixture import fixture_capability
from runtime.abi3.layout import RecordError
from runtime.abi3.request import (
    REQUEST_DESCRIPTOR_HEADER,
    RequestSymbolDescriptor,
    RequestSymbolEntry,
)
from runtime.abi3.verifier import VerificationError, verify_request_symbol_descriptor


def _symbols(*, batch: int = 1) -> dict[int, int]:
    return {
        int(Symbol.SPAN_TOKENS): 3,
        int(Symbol.POSITION_START): 4,
        int(Symbol.POSITION_END): 7,
        int(Symbol.CONTEXT_LENGTH): 7,
        int(Symbol.PHASE): int(Phase.DECODE),
        int(Symbol.GENERATION_INDEX): 2,
        int(Symbol.MAX_NEW_TOKENS): 8,
        int(Symbol.BATCH): batch,
        int(Symbol.NODE_ID): 0,
        int(Symbol.NODE_COUNT): 1,
        int(Symbol.ACTIVE_EXPERT_COUNT): 0,
        int(Symbol.SPARSE_INDEX_COUNT): 0,
        int(Symbol.LAYER_COUNT): 36,
        int(Symbol.VOCABULARY_PARTITIONS): 1,
        int(Symbol.SPAN_LAST_INDEX): 2,
    }


def _descriptor(*, batch: int = 1) -> RequestSymbolDescriptor:
    return RequestSymbolDescriptor.from_symbols(
        request_descriptor_id=9,
        deployment_id=10,
        deployment_generation=11,
        session_id=12,
        session_generation=13,
        transaction_id=14,
        symbols=_symbols(batch=batch),
    )


def _reseal_crc(record: bytes) -> bytes:
    edited = bytearray(record)
    offset = REQUEST_DESCRIPTOR_HEADER.crc_offset()
    edited[offset : offset + 4] = bytes(4)
    edited[offset : offset + 4] = record_crc(bytes(edited), offset).to_bytes(
        4, "little"
    )
    return bytes(edited)


def test_request_symbol_descriptor_round_trips_deterministically() -> None:
    descriptor = _descriptor()
    record = descriptor.encode()

    assert len(record) == 384
    assert len(record) % DESCRIPTOR_ALIGNMENT == 0
    assert record == descriptor.encode()
    assert RequestSymbolDescriptor.decode(record) == descriptor
    assert [entry.symbol_id for entry in descriptor.entries] == sorted(_symbols())
    assert verify_request_symbol_descriptor(
        RequestSymbolDescriptor.decode(record), fixture_capability()
    ) == _symbols()


def test_request_descriptor_rejects_corrupted_crc_and_digest() -> None:
    record = bytearray(_descriptor().encode())
    record[REQUEST_DESCRIPTOR_HEADER.crc_offset()] ^= 0x80
    with pytest.raises(RecordError, match="CRC32C"):
        RequestSymbolDescriptor.decode(bytes(record))

    record = bytearray(_descriptor().encode())
    first_value = REQUEST_DESCRIPTOR_HEADER.size + 8
    record[first_value] ^= 0x01
    with pytest.raises(RecordError, match="SHA-256"):
        RequestSymbolDescriptor.decode(_reseal_crc(bytes(record)))


@pytest.mark.parametrize("malformation", ["missing", "unknown", "duplicate"])
def test_request_verifier_rejects_noncanonical_symbol_sets(
    malformation: str,
) -> None:
    descriptor = _descriptor()
    entries = list(descriptor.entries)
    if malformation == "missing":
        entries = [
            entry for entry in entries if entry.symbol_id != int(Symbol.BATCH)
        ]
        pattern = "missing required symbols"
    elif malformation == "unknown":
        entries[0] = RequestSymbolEntry(0xFFFF, entries[0].value)
        pattern = "unknown symbol ID"
    else:
        entries.append(RequestSymbolEntry(int(Symbol.BATCH), 1))
        pattern = "repeats symbol BATCH"

    malformed = replace(descriptor, entries=tuple(entries))
    decoded = RequestSymbolDescriptor.decode(malformed.encode())
    with pytest.raises(VerificationError, match=pattern):
        verify_request_symbol_descriptor(decoded, fixture_capability())


def test_request_verifier_applies_the_physical_session_bound_to_batch() -> None:
    descriptor = _descriptor(batch=fixture_capability().limits["max_sessions"] + 1)
    with pytest.raises(VerificationError, match="BATCH.*exceeds"):
        verify_request_symbol_descriptor(descriptor, fixture_capability())
