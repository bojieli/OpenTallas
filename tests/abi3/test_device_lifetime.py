"""A failed transaction must not retain its activated device through a traceback."""

from __future__ import annotations

import gc
import weakref
from dataclasses import replace

from runtime.abi3.constants import CompletionStatus, TrapClass
from runtime.sim.device import Device

from . import probe_capability, probe_deployment


def test_watchdog_trap_does_not_retain_the_device_until_cyclic_gc() -> None:
    """Transaction failures expose records, not exception traceback lifetimes."""
    gc_was_enabled = gc.isenabled()
    gc.disable()
    device_ref: weakref.ReferenceType[Device] | None = None
    try:
        capability = probe_capability()
        deployment = probe_deployment(capability)
        device = Device(deployment, capability, verify=False)
        device.header = replace(device.header, max_retired_work=0)
        session = device.create_session()
        device_ref = weakref.ref(device)

        result = device.run_transaction(session, entrypoint_id=0, symbols={})
        assert result.status == CompletionStatus.FAILED
        assert result.trap_class == TrapClass.TIMEOUT_OR_WATCHDOG
        assert result.first_fault_instruction == 1
        assert result.message == "retired work exceeded the verified bound 0"

        del result, session, device
        assert device_ref() is None
    finally:
        if gc_was_enabled:
            gc.enable()
        if device_ref is not None and device_ref() is not None:
            gc.collect()
