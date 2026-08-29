"""Event-driven ABI 3.0 cycle model.

One model, four targets.  The cycle model consumes *exactly* the artifacts the
functional device consumes -- a :class:`~runtime.abi3.deployment.Deployment`, a
:class:`~runtime.abi3.capability.Capability` and a request -- and it obtains its
architectural events by *running the functional device itself*
(:class:`~runtime.sim.device.Device`) with instrumentation hooks.  That is a
deliberate structural choice rather than a shortcut:

* ADR-003 section 13 requires the functional simulator, the cycle simulator and
  RTL to share one counter definition.  A cycle model that re-implemented the
  microsequencer would drift from the functional one the first time either
  changed.  Here they cannot drift, because there is one microsequencer;
* the requirement is that every *architectural* counter agree exactly.  Running
  the same code path makes that agreement a theorem rather than a test result --
  the test still checks it, but it checks a property that is true by
  construction;
* timing counters (frozen registry group ``0x0c``) are the only counters the
  cycle model adds.  The functional device leaves all of them at zero.

What the cycle model adds on top of that execution is a real machine:

``microsequencer``
    in-order fetch/decode/predicate/issue with a bounded issue port;
``engine queues``
    per-family bounded submission queues with a depth and an outstanding limit
    taken from the capability, and credit-gated issue;
``engines``
    occupancy and fixed latency per family, throughput from lanes and rate;
``memory hierarchy``
    HBM channels with per-channel bandwidth and latency, SRAM banks with port
    conflicts, and immutable ROM in its own bandwidth/latency class, all
    addressed by real object addresses so that contention is physical;
``scoreboard``
    single-assignment events with acquire waits, which is what makes a stall a
    stall rather than a fudge factor;
``fabric``
    :mod:`runtime.cycle.fabric` for the 32-node cluster and the wafer.

Two invariants are *proved*, not asserted in prose (ADR-003 section 9): bounded
queue occupancy for the admitted schedule, and absence of cyclic waits.  And no
global barrier or collective is ever modelled as zero-latency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CompletionStatus,
    Control,
    DTYPE_BITS,
    Major,
    NO_ID,
    StorageClass,
    TopologyClass,
    TrapClass,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import (
    CollectiveOp,
    Descriptor,
    ExtendedDescriptorType,
    Link,
    Phase,
    SelectorKind,
    Symbol,
) if False else None  # placeholder replaced below
