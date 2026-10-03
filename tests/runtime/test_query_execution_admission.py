"""Specialized bounds must refuse at the actual queue and direct entry path."""
from dataclasses import replace
import pytest

from compiler.frontends.v3.deepseek_v41 import query_execution_contract
from runtime.abi3.constants import HostOpcode, NO_ID, StorageClass, SubmissionFlag, CompletionStatus
from runtime.abi3.descriptors import Phase, Symbol
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.abi3.records import Submission, split_program
from runtime.abi3.request import RequestSymbolDescriptor
from runtime.sim.device import Device, DeviceTrap


def device_and_symbols(span=1, start=0):
    capability = fixture_capability()
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    deployment.notes["query_execution"] = query_execution_contract(16, execution_mode="decode")
    header, _ = split_program(deployment.program)
    deployment.program = replace(header, deployment_digest=deployment.deployment_digest).encode() + deployment.program[256:]
    device = Device(deployment, capability)
    symbols = {
        int(Symbol.SPAN_TOKENS): span, int(Symbol.POSITION_START): start,
        int(Symbol.POSITION_END): start+span, int(Symbol.CONTEXT_LENGTH): start+span,
        int(Symbol.PHASE): int(Phase.PREFILL), int(Symbol.GENERATION_INDEX): 0,
        int(Symbol.MAX_NEW_TOKENS): 2, int(Symbol.BATCH): 1,
        int(Symbol.NODE_ID): 0, int(Symbol.NODE_COUNT): device.node_count,
        int(Symbol.ACTIVE_EXPERT_COUNT): 0, int(Symbol.SPARSE_INDEX_COUNT): 0,
        int(Symbol.LAYER_COUNT): 0, int(Symbol.VOCABULARY_PARTITIONS): 1,
        int(Symbol.SPAN_LAST_INDEX): span-1,
    }
    return device, symbols


def test_actual_queue_rejects_prefill_before_engine_issue(monkeypatch):
    device, symbols = device_and_symbols()
    session = device.create_session()
    original_generation = session.generation
    descriptor_id = device.next_request_descriptor_id
    descriptor = RequestSymbolDescriptor.from_symbols(
        request_descriptor_id=descriptor_id, deployment_id=device.deployment.deployment_id,
        deployment_generation=device.deployment.generation, session_id=session.session_id,
        session_generation=session.generation, transaction_id=1, symbols=symbols,
    )
    device.register_request_descriptor(descriptor.encode())
    request = Submission(
        host_opcode=int(HostOpcode.GENERATE), deployment_id=device.deployment.deployment_id,
        deployment_generation=device.deployment.generation, session_id=session.session_id,
        session_generation=session.generation, transaction_id=1,
        request_descriptor_id=descriptor_id, entrypoint_id=0, generation_policy_id=NO_ID,
        flags=int(SubmissionFlag.PREFILL_PHASE),
    )
    monkeypatch.setattr(device, "run_transaction", lambda *a, **k: pytest.fail("engine issued"))
    with pytest.raises(DeviceTrap, match="compiled phase bound 0"):
        device.prepare_request(request)
    assert session.generation == original_generation and session.position == 0 and not session.generated


def test_direct_path_also_refuses_wrong_span():
    device, symbols = device_and_symbols(span=2)
    symbols[int(Symbol.PHASE)] = int(Phase.DECODE)
    session = device.create_session()
    original_generation = session.generation
    result = device.run_transaction(session, entrypoint_id=1, symbols=symbols)
    assert result.status == CompletionStatus.FAILED
    assert "compiled phase bound 1" in result.message
    assert result.retired == 0 and session.generation == original_generation
