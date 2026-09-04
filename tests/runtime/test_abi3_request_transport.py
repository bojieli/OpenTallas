"""Focused queue-lifetime tests for authenticated request-symbol transport."""

from __future__ import annotations

from dataclasses import replace

import pytest

from runtime.abi3.constants import (
    CompletionStatus,
    HostOpcode,
    NO_ID,
    StorageClass,
    SubmissionFlag,
    TrapClass,
)
from runtime.abi3.descriptors import Phase, Symbol
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.abi3.records import Submission
from runtime.abi3.request import RequestSymbolDescriptor
from runtime.sim.device import Device, DeviceTrap
from runtime.sim.engines import load_engines


def _device() -> Device:
    capability = fixture_capability()
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    return Device(deployment, capability)


def _symbols(device: Device, *, batch: int = 1) -> dict[int, int]:
    return {
        int(Symbol.SPAN_TOKENS): 1,
        int(Symbol.POSITION_START): 0,
        int(Symbol.POSITION_END): 1,
        int(Symbol.CONTEXT_LENGTH): 1,
        int(Symbol.PHASE): int(Phase.PREFILL),
        int(Symbol.GENERATION_INDEX): 0,
        int(Symbol.MAX_NEW_TOKENS): 2,
        int(Symbol.BATCH): batch,
        int(Symbol.NODE_ID): 0,
        int(Symbol.NODE_COUNT): device.node_count,
        int(Symbol.ACTIVE_EXPERT_COUNT): 0,
        int(Symbol.SPARSE_INDEX_COUNT): 0,
        int(Symbol.LAYER_COUNT): 0,
        int(Symbol.VOCABULARY_PARTITIONS): 1,
        int(Symbol.SPAN_LAST_INDEX): 0,
    }


def _register(
    device: Device,
    session,
    *,
    transaction_id: int,
    symbols: dict[int, int] | None = None,
) -> int:
    descriptor_id = device.next_request_descriptor_id
    descriptor = RequestSymbolDescriptor.from_symbols(
        request_descriptor_id=descriptor_id,
        deployment_id=device.deployment.deployment_id,
        deployment_generation=device.deployment.generation,
        session_id=session.session_id,
        session_generation=session.generation,
        transaction_id=transaction_id,
        symbols=_symbols(device) if symbols is None else symbols,
    )
    assert device.register_request_descriptor(descriptor.encode()) == descriptor_id
    return descriptor_id


def _submission(
    device: Device,
    session,
    *,
    descriptor_id: int,
    transaction_id: int,
    session_id: int | None = None,
    session_generation: int | None = None,
) -> bytes:
    return Submission(
        host_opcode=int(HostOpcode.GENERATE),
        deployment_id=device.deployment.deployment_id,
        deployment_generation=device.deployment.generation,
        session_id=session.session_id if session_id is None else session_id,
        session_generation=(
            session.generation
            if session_generation is None
            else session_generation
        ),
        request_descriptor_id=descriptor_id,
        transaction_id=transaction_id,
        entrypoint_id=0,
        generation_policy_id=NO_ID,
        flags=int(SubmissionFlag.PREFILL_PHASE),
    ).encode()


def test_scalar_queue_executes_the_exact_registered_symbol_map(monkeypatch) -> None:
    load_engines()
    device = _device()
    session = device.create_session()
    symbols = _symbols(device)
    descriptor_id = _register(device, session, transaction_id=1, symbols=symbols)
    request = _submission(
        device, session, descriptor_id=descriptor_id, transaction_id=1
    )
    observed: dict[int, int] = {}
    original = device.run_transaction

    def capture(*args, **kwargs):
        observed.update(kwargs["symbols"])
        return original(*args, **kwargs)

    monkeypatch.setattr(device, "run_transaction", capture)
    completion_record, result = device.execute_submission(request)

    assert result.status == CompletionStatus.SUCCESS, result.message
    assert observed == symbols
    assert Submission.decode(request).request_descriptor_id == descriptor_id
    assert device.live_request_descriptor_count == 0
    assert device.last_request_descriptor is not None
    assert device.last_request_descriptor.symbol_map() == symbols
    assert completion_record[:4] == b"TA3C"


@pytest.mark.parametrize(
    ("descriptor_id", "trap", "message"),
    [
        (NO_ID, TrapClass.DESCRIPTOR_OR_ADDRESS, "missing request_descriptor_id"),
        (77, TrapClass.AUTHENTICATION_OR_INTEGRITY, "unknown, stale"),
    ],
)
def test_missing_or_unknown_descriptor_fails_before_work(
    descriptor_id: int, trap: TrapClass, message: str
) -> None:
    device = _device()
    session = device.create_session()
    request = _submission(
        device, session, descriptor_id=descriptor_id, transaction_id=1
    )

    _completion, result = device.execute_submission(request)

    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == trap
    assert message in result.message
    assert result.retired == 0


def test_request_descriptor_cannot_cross_sessions() -> None:
    device = _device()
    owner = device.create_session()
    other = device.create_session()
    descriptor_id = _register(device, owner, transaction_id=1)
    request = _submission(
        device,
        other,
        descriptor_id=descriptor_id,
        transaction_id=1,
    )

    _completion, result = device.execute_submission(request)

    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.STATE_TRANSACTION
    assert "binds session_id" in result.message
    assert device.live_request_descriptor_count == 0


def test_request_descriptor_cannot_cross_transactions() -> None:
    device = _device()
    session = device.create_session()
    descriptor_id = _register(device, session, transaction_id=8)
    request = _submission(
        device, session, descriptor_id=descriptor_id, transaction_id=9
    )

    _completion, result = device.execute_submission(request)

    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.STATE_TRANSACTION
    assert "binds transaction_id=8" in result.message
    assert device.live_request_descriptor_count == 0


def test_request_descriptor_expires_when_the_session_generation_advances() -> None:
    device = _device()
    session = device.create_session()
    descriptor_id = _register(device, session, transaction_id=1)
    bound_generation = session.generation
    session.generation += 1
    request = _submission(
        device,
        session,
        descriptor_id=descriptor_id,
        transaction_id=1,
        session_generation=bound_generation,
    )

    _completion, result = device.execute_submission(request)

    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.STATE_TRANSACTION
    assert "stale; live generation" in result.message
    assert device.live_request_descriptor_count == 0


def test_consumed_request_descriptor_cannot_be_replayed() -> None:
    device = _device()
    session = device.create_session()
    descriptor_id = _register(device, session, transaction_id=1)
    request = Submission.decode(
        _submission(device, session, descriptor_id=descriptor_id, transaction_id=1)
    )

    prepared = device.prepare_request(request)
    assert prepared.symbols == _symbols(device)
    assert device.live_request_descriptor_count == 0
    with pytest.raises(DeviceTrap, match="already consumed"):
        device.prepare_request(request)


def test_registration_and_resolution_both_authenticate_descriptor_bytes() -> None:
    device = _device()
    session = device.create_session()
    descriptor_id = device.next_request_descriptor_id
    descriptor = RequestSymbolDescriptor.from_symbols(
        request_descriptor_id=descriptor_id,
        deployment_id=device.deployment.deployment_id,
        deployment_generation=device.deployment.generation,
        session_id=session.session_id,
        session_generation=session.generation,
        transaction_id=1,
        symbols=_symbols(device),
    )
    corrupt = bytearray(descriptor.encode())
    corrupt[-1] ^= 0x01
    with pytest.raises(DeviceTrap, match="integrity admission"):
        device.register_request_descriptor(bytes(corrupt))

    descriptor_id = _register(device, session, transaction_id=1)
    registered = device._request_descriptors[descriptor_id]
    changed = registered.record[:-1] + bytes([registered.record[-1] ^ 0x01])
    device._request_descriptors[descriptor_id] = replace(registered, record=changed)
    request = _submission(
        device, session, descriptor_id=descriptor_id, transaction_id=1
    )
    _completion, result = device.execute_submission(request)
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.AUTHENTICATION_OR_INTEGRITY
    assert "changed after admission" in result.message


def test_request_descriptor_pool_is_bounded_and_session_owned() -> None:
    device = _device()
    capacity = device.capability.limits["max_sessions"]
    sessions = [device.create_session() for _ in range(capacity + 1)]
    descriptor_ids = [
        _register(device, session, transaction_id=index + 1)
        for index, session in enumerate(sessions[:capacity])
    ]
    assert device.live_request_descriptor_count == capacity

    descriptor_id = device.next_request_descriptor_id
    descriptor = RequestSymbolDescriptor.from_symbols(
        request_descriptor_id=descriptor_id,
        deployment_id=device.deployment.deployment_id,
        deployment_generation=device.deployment.generation,
        session_id=sessions[-1].session_id,
        session_generation=sessions[-1].generation,
        transaction_id=capacity + 1,
        symbols=_symbols(device),
    )
    with pytest.raises(DeviceTrap, match="pool is full"):
        device.register_request_descriptor(descriptor.encode())

    device.discard_request_descriptors(descriptor_ids)
    assert device.live_request_descriptor_count == 0
