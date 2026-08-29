"""Physical fabric models for the ABI 3.0 cycle model.

ADR-003 section 8.8 makes inter-chip and on-wafer communication a *first-class
accelerator engine*, and section 3.3 makes the two physical realisations
mandatory and non-interchangeable:

* the 32-node conventional-chip cluster, whose fabric is an NVLink-class
  external switch network -- link serialisation, per-hop wire and SerDes
  latency, switch contention, credits and retry;
* the wafer-scale logical device, whose fabric is an on-wafer reticle/tile mesh
  -- dimension-ordered routing, reticle stitch crossings with their own
  bandwidth and latency class, congestion, and *bounded* global barriers.

They are two realisations of one architectural contract, so both expose the same
interface (:meth:`unicast`, :meth:`collective`, :meth:`barrier`) and both feed
the same frozen counter registry.  ADR-003 section 9 is explicit that neither
simulator may model a global barrier or collective as zero-latency; every method
here therefore costs at least one endpoint latency, and
:func:`assert_no_zero_latency_global_operations` checks it.

A collective is executed as an *algorithm over the link resources*, not as a
closed-form penalty: a ring all-reduce really is ``2*(P-1)`` neighbour transfers
that contend for the same ports, and a broadcast really is a tree of unicasts.
That is what makes the reported collective time comparable with the reported
link time on the same fabric.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Mapping, Sequence

from runtime.abi3.constants import TopologyClass
from runtime.abi3.descriptors import CollectiveOp
from runtime.cycle.machine import (
    ClusterFabricParams,
    MachineError,
    MachineModel,
    WaferFabricParams,
)


class FabricError(ValueError):
    """Raised when a fabric request is not expressible on this topology."""


# ---------------------------------------------------------------------------
# Timing record
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class FabricTiming:
    """The cost of one communication operation, broken out by cause.

    Nothing here is blended: serialisation, hop latency, switch contention,
    credit stall and retry are separate because ADR-003 section 3.3 requires
    actual link latency, serialization, switch contention, bandwidth, retry and
    congestion modelling -- a single aggregate number would not be checkable.
    """

    operation: str
    start_cycle: int = 0
    end_cycle: int = 0
    serialization_cycles: int = 0
    hop_cycles: int = 0
    switch_contention_cycles: int = 0
    credit_stall_cycles: int = 0
    retry_cycles: int = 0
    endpoint_cycles: int = 0
    bytes_moved: int = 0
    wire_bytes: int = 0
    packets: int = 0
    messages: int = 0
    retries: int = 0
    hops: int = 0
    participants: int = 0
    steps: int = 0
    algorithm: str = ""

    @property
    def cycles(self) -> int:
        return max(self.end_cycle - self.start_cycle, 0)

    def merge(self, other: "FabricTiming") -> None:
        """Accumulate ``other``'s cost; the caller owns the overall span.

        Cause breakdowns add (they are totals over every packet on every link);
        the span is a union, because the steps of a collective overlap in time.
        """
        self.end_cycle = max(self.end_cycle, other.end_cycle)
        self.serialization_cycles += other.serialization_cycles
        self.hop_cycles += other.hop_cycles
        self.switch_contention_cycles += other.switch_contention_cycles
        self.credit_stall_cycles += other.credit_stall_cycles
        self.retry_cycles += other.retry_cycles
        self.endpoint_cycles += other.endpoint_cycles
        self.bytes_moved += other.bytes_moved
        self.wire_bytes += other.wire_bytes
        self.packets += other.packets
        self.messages += other.messages
        self.retries += other.retries
        self.hops += other.hops
        self.steps += other.steps

    def counters(self) -> dict[str, int]:
        """Frozen-registry counter deltas produced by this operation.

        Architectural counters (group 0x0a) and timing counters (group 0x0c) are
        both returned; the caller decides which of the two it may apply.
        """
        return {
            "link.messages_sent": self.messages,
            "link.messages_received": self.messages,
            "link.bytes_sent": self.bytes_moved,
            "link.bytes_received": self.bytes_moved,
            "link.retries": self.retries,
            "link.credit_stalls": 1 if self.credit_stall_cycles else 0,
            "latency.link_serialization_cycles": self.serialization_cycles,
            "latency.link_hop_cycles": self.hop_cycles,
            "latency.link_switch_contention_cycles": self.switch_contention_cycles,
            "latency.link_credit_stall_cycles": self.credit_stall_cycles,
            "latency.link_retry_cycles": self.retry_cycles,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "algorithm": self.algorithm,
            "start_cycle": self.start_cycle,
            "end_cycle": self.end_cycle,
            "cycles": self.cycles,
            "serialization_cycles": self.serialization_cycles,
            "hop_cycles": self.hop_cycles,
            "switch_contention_cycles": self.switch_contention_cycles,
            "credit_stall_cycles": self.credit_stall_cycles,
            "retry_cycles": self.retry_cycles,
            "endpoint_cycles": self.endpoint_cycles,
            "bytes_moved": self.bytes_moved,
            "wire_bytes": self.wire_bytes,
            "packets": self.packets,
            "messages": self.messages,
            "retries": self.retries,
            "hops": self.hops,
            "participants": self.participants,
            "steps": self.steps,
        }


# ---------------------------------------------------------------------------
# Shared link resource
# ---------------------------------------------------------------------------
class _Port:
    """One serialising resource: a link, a switch output port, a mesh edge."""

    __slots__ = ("name", "bytes_per_cycle", "free_at", "busy_cycles", "contention_cycles")

    def __init__(self, name: str, bytes_per_cycle: float) -> None:
        if bytes_per_cycle <= 0:
            raise MachineError(f"port {name} has non-positive bandwidth")
        self.name = name
        self.bytes_per_cycle = bytes_per_cycle
        self.free_at = 0
        self.busy_cycles = 0
        self.contention_cycles = 0

    def serialization_cycles(self, nbytes: int) -> int:
        return max(1, math.ceil(nbytes / self.bytes_per_cycle))

    def occupy(self, arrival: int, nbytes: int) -> tuple[int, int, int]:
        """Reserve the port for ``nbytes`` arriving at ``arrival``.

        Returns ``(departure, serialization, contention)``.  ``contention`` is
        the number of cycles the packet waited because the port was already
        carrying somebody else's traffic; that is the switch/link contention the
        cluster contract requires to be reported separately.
        """
        contention = max(0, self.free_at - arrival)
        start = arrival + contention
        cycles = self.serialization_cycles(nbytes)
        self.free_at = start + cycles
        self.busy_cycles += cycles
        self.contention_cycles += contention
        return self.free_at, cycles, contention

    def reserve_bulk(self, arrival: int, cycles: int) -> tuple[int, int]:
        """Reserve ``cycles`` of port time without per-packet bookkeeping."""
        contention = max(0, self.free_at - arrival)
        start = arrival + contention
        self.free_at = start + cycles
        self.busy_cycles += cycles
        self.contention_cycles += contention
        return self.free_at, contention


@dataclass(frozen=True, slots=True)
class _Route:
    """An ordered list of ports plus the fixed latency along the path."""

    ports: tuple[_Port, ...]
    hop_latency_cycles: int
    hops: int
    description: str


class _FabricBase:
    """Shared packetisation, credit and retry machinery."""

    #: Beyond this many packets in one transfer the model reserves port time in
    #: bulk instead of walking every packet.  The reservation is exact in total
    #: occupancy; only the interleaving with other traffic is coarsened.  This
    #: keeps a 16 GB remote transfer from costing 250 million events.
    MAX_MODELED_PACKETS = 4096

    def __init__(self, *, packet_bytes: int, header_bytes: int, credits: int,
                 credit_return_cycles: int, retry_interval_packets: int,
                 retry_cycles: int, endpoint_latency_cycles: int) -> None:
        if header_bytes >= packet_bytes:
            raise MachineError("packet header must be smaller than the packet")
        self.packet_bytes = packet_bytes
        self.header_bytes = header_bytes
        self.payload_bytes = packet_bytes - header_bytes
        self.credits = credits
        self.credit_return_cycles = credit_return_cycles
        self.retry_interval_packets = retry_interval_packets
        self.retry_cycles = retry_cycles
        self.endpoint_latency_cycles = endpoint_latency_cycles

    # -- routing (subclass) ---------------------------------------------
    def route(self, src: int, dst: int) -> _Route:  # pragma: no cover - abstract
        raise NotImplementedError

    def endpoints(self) -> int:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- one directed transfer -------------------------------------------
    def unicast(
        self,
        src: int,
        dst: int,
        nbytes: int,
        *,
        start_cycle: int = 0,
        operation: str = "unicast",
    ) -> FabricTiming:
        """Move ``nbytes`` from ``src`` to ``dst``, packet by packet."""
        endpoints = self.endpoints()
        for node in (src, dst):
            if not 0 <= node < endpoints:
                raise FabricError(
                    f"endpoint {node} is outside the {endpoints}-endpoint fabric"
                )
        timing = FabricTiming(
            operation=operation,
            start_cycle=start_cycle,
            end_cycle=start_cycle,
            participants=1 if src == dst else 2,
            steps=1,
            algorithm="packetised_unicast",
        )
        if nbytes <= 0 or src == dst:
            # A zero-byte or loopback message still costs the endpoint: an
            # architecturally visible message is never free.
            timing.end_cycle = start_cycle + self.endpoint_latency_cycles
            timing.endpoint_cycles = self.endpoint_latency_cycles
            timing.messages = 1
            return timing
        route = self.route(src, dst)
        packets = max(1, math.ceil(nbytes / self.payload_bytes))
        retries = packets // self.retry_interval_packets
        timing.bytes_moved = nbytes
        timing.packets = packets
        timing.messages = 1
        timing.retries = retries
        timing.hops = route.hops
        timing.hop_cycles = route.hop_latency_cycles
        timing.endpoint_cycles = 2 * self.endpoint_latency_cycles
        timing.wire_bytes = packets * self.packet_bytes

        launch = start_cycle + self.endpoint_latency_cycles
        if packets <= self.MAX_MODELED_PACKETS:
            arrivals: list[int] = []
            last_arrival = launch
            for index in range(packets):
                ready = launch
                if index >= self.credits:
                    returned = arrivals[index - self.credits] + self.credit_return_cycles
                    if returned > ready:
                        timing.credit_stall_cycles += returned - ready
                        ready = returned
                time = ready
                for hop, port in enumerate(route.ports):
                    time, serial, contention = port.occupy(time, self.packet_bytes)
                    timing.serialization_cycles += serial
                    timing.switch_contention_cycles += contention
                    if hop == 0:
                        # The next packet may enter the first port as soon as
                        # this one has cleared it: that is what makes a long
                        # transfer bandwidth-bound rather than latency-bound.
                        launch = time
                time += route.hop_latency_cycles
                if (index + 1) % self.retry_interval_packets == 0:
                    time += self.retry_cycles
                    timing.retry_cycles += self.retry_cycles
                arrivals.append(time)
                last_arrival = max(last_arrival, time)
            timing.end_cycle = last_arrival + self.endpoint_latency_cycles
        else:
            cursor = launch
            timing.end_cycle, bulk = self._bulk_transfer(route, cursor, packets)
            timing.serialization_cycles += bulk["serialization"]
            timing.switch_contention_cycles += bulk["contention"]
            timing.credit_stall_cycles += bulk["credit_stall"]
            timing.retry_cycles += retries * self.retry_cycles
            timing.end_cycle += retries * self.retry_cycles
        return timing

    def _bulk_transfer(
        self, route: _Route, start: int, packets: int
    ) -> tuple[int, dict[str, int]]:
        """Reserve whole-transfer port time without per-packet events."""
        serialization = 0
        contention = 0
        time = start
        for port in route.ports:
            cycles = port.serialization_cycles(self.packet_bytes) * packets
            time, waited = port.reserve_bulk(time, cycles)
            serialization += cycles
            contention += waited
        # A credit-limited pipeline cannot go faster than one credit window per
        # round trip; that floor is real and is reported as a credit stall.
        window = max(1, self.credits)
        floor = (
            math.ceil(packets / window)
            * (route.hop_latency_cycles + self.credit_return_cycles)
        )
        span = time - start
        credit_stall = max(0, floor - span)
        return (
            time + credit_stall + route.hop_latency_cycles + self.endpoint_latency_cycles,
            {
                "serialization": serialization,
                "contention": contention,
                "credit_stall": credit_stall,
            },
        )

    # -- collectives -------------------------------------------------------
    def collective(
        self,
        op: int,
        participants: Sequence[int],
        nbytes: int,
        *,
        start_cycle: int = 0,
        chunk_bytes: int = 0,
    ) -> FabricTiming:
        """Run one collective as an actual algorithm over the link resources."""
        members = list(dict.fromkeys(int(p) for p in participants))
        count = len(members)
        if count == 0:
            raise FabricError("a collective needs at least one participant")
        operation = CollectiveOp(int(op)).name
        total = FabricTiming(
            operation=f"collective.{operation}",
            start_cycle=start_cycle,
            end_cycle=start_cycle + self.endpoint_latency_cycles,
            participants=count,
            algorithm="single_participant",
        )
        total.endpoint_cycles = self.endpoint_latency_cycles
        if count == 1:
            total.messages = 1
            return total
        collective = CollectiveOp(int(op))
        if collective is CollectiveOp.POINT_TO_POINT:
            step = self.unicast(
                members[0], members[-1], nbytes, start_cycle=start_cycle,
                operation="collective.POINT_TO_POINT",
            )
            step.participants = count
            step.algorithm = "point_to_point"
            return step
        if collective in (CollectiveOp.SUM, CollectiveOp.MAX, CollectiveOp.MIN):
            return self._ring(
                members, nbytes, start_cycle, rounds=2 * (count - 1),
                operation=f"collective.{operation}",
                algorithm="ring_reduce_scatter_then_all_gather",
            )
        if collective is CollectiveOp.ALL_GATHER:
            return self._ring(
                members, nbytes, start_cycle, rounds=count - 1,
                operation=f"collective.{operation}", algorithm="ring_all_gather",
            )
        if collective is CollectiveOp.REDUCE_SCATTER:
            return self._ring(
                members, nbytes, start_cycle, rounds=count - 1,
                operation=f"collective.{operation}", algorithm="ring_reduce_scatter",
            )
        if collective is CollectiveOp.BROADCAST:
            return self._tree(
                members, nbytes, start_cycle,
                operation=f"collective.{operation}", algorithm="binomial_tree_broadcast",
            )
        if collective is CollectiveOp.CONCAT:
            return self._gather(
                members, nbytes, start_cycle,
                operation=f"collective.{operation}", algorithm="root_gather",
            )
        raise FabricError(f"collective {operation} is not modelled")

    def _ring(
        self,
        members: Sequence[int],
        nbytes: int,
        start_cycle: int,
        *,
        rounds: int,
        operation: str,
        algorithm: str,
    ) -> FabricTiming:
        count = len(members)
        per_step = max(1, math.ceil(nbytes / count))
        total = FabricTiming(
            operation=operation,
            start_cycle=start_cycle,
            end_cycle=start_cycle,
            participants=count,
            algorithm=algorithm,
        )
        cursor = start_cycle
        for _ in range(rounds):
            round_end = cursor
            for index, node in enumerate(members):
                peer = members[(index + 1) % count]
                step = self.unicast(
                    node, peer, per_step, start_cycle=cursor, operation=operation
                )
                total.merge(step)
                round_end = max(round_end, step.end_cycle)
            cursor = round_end  # a ring step is a synchronising round
            total.steps += 1
        total.start_cycle = start_cycle
        total.end_cycle = max(cursor, start_cycle + self.endpoint_latency_cycles)
        return total

    def _tree(
        self,
        members: Sequence[int],
        nbytes: int,
        start_cycle: int,
        *,
        operation: str,
        algorithm: str,
    ) -> FabricTiming:
        count = len(members)
        total = FabricTiming(
            operation=operation,
            start_cycle=start_cycle,
            end_cycle=start_cycle,
            participants=count,
            algorithm=algorithm,
        )
        have = [start_cycle] + [0] * (count - 1)
        reached = 1
        cursor = start_cycle
        while reached < count:
            round_end = cursor
            for index in range(min(reached, count - reached)):
                target = reached + index
                step = self.unicast(
                    members[index],
                    members[target],
                    nbytes,
                    start_cycle=have[index],
                    operation=operation,
                )
                total.merge(step)
                have[target] = step.end_cycle
                round_end = max(round_end, step.end_cycle)
            reached = min(count, reached * 2)
            cursor = round_end
            total.steps += 1
        total.start_cycle = start_cycle
        total.end_cycle = max(cursor, start_cycle + self.endpoint_latency_cycles)
        return total

    def _gather(
        self,
        members: Sequence[int],
        nbytes: int,
        start_cycle: int,
        *,
        operation: str,
        algorithm: str,
    ) -> FabricTiming:
        count = len(members)
        per_member = max(1, math.ceil(nbytes / count))
        total = FabricTiming(
            operation=operation,
            start_cycle=start_cycle,
            end_cycle=start_cycle,
            participants=count,
            algorithm=algorithm,
        )
        root = members[0]
        end = start_cycle
        for node in members[1:]:
            step = self.unicast(
                node, root, per_member, start_cycle=start_cycle, operation=operation
            )
            total.merge(step)
            end = max(end, step.end_cycle)
        total.steps = count - 1
        total.start_cycle = start_cycle
        total.end_cycle = max(end, start_cycle + self.endpoint_latency_cycles)
        return total

    # -- barrier -----------------------------------------------------------
    def barrier(
        self, participants: Sequence[int], *, start_cycle: int = 0
    ) -> FabricTiming:
        """A bounded, non-zero global barrier (ADR-003 section 9)."""
        members = list(dict.fromkeys(int(p) for p in participants))
        count = len(members)
        if count == 0:
            raise FabricError("a barrier needs at least one participant")
        total = FabricTiming(
            operation="barrier",
            start_cycle=start_cycle,
            end_cycle=start_cycle,
            participants=count,
            algorithm="dissemination",
        )
        rounds = max(1, math.ceil(math.log2(count))) if count > 1 else 1
        cursor = start_cycle
        for round_index in range(rounds):
            distance = 1 << round_index
            round_end = cursor
            for index, node in enumerate(members):
                peer = members[(index + distance) % count]
                step = self.unicast(
                    node, peer, self.header_bytes, start_cycle=cursor,
                    operation="barrier",
                )
                total.merge(step)
                round_end = max(round_end, step.end_cycle)
            cursor = round_end + self._barrier_round_cycles()
            total.steps += 1
        total.start_cycle = start_cycle
        total.end_cycle = max(cursor, start_cycle + self.endpoint_latency_cycles)
        return total

    def _barrier_round_cycles(self) -> int:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- reporting ---------------------------------------------------------
    def port_report(self, limit: int = 16) -> dict[str, Any]:
        ports = sorted(
            self._all_ports(), key=lambda p: (-p.busy_cycles, p.name)
        )
        busy = sum(p.busy_cycles for p in ports)
        contention = sum(p.contention_cycles for p in ports)
        return {
            "port_count": len(ports),
            "total_busy_cycles": busy,
            "total_contention_cycles": contention,
            "busiest": [
                {
                    "port": p.name,
                    "busy_cycles": p.busy_cycles,
                    "contention_cycles": p.contention_cycles,
                }
                for p in ports[:limit]
                if p.busy_cycles
            ],
        }

    def _all_ports(self) -> list[_Port]:  # pragma: no cover - abstract
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 32-node conventional-chip cluster
# ---------------------------------------------------------------------------
class ClusterFabric(_FabricBase):
    """The inter-node fabric of the 32-node conventional-chip cluster.

    Physical realisation: each node's synthesizable endpoint drives one or more
    external high-speed links into a switch hierarchy.  A packet therefore
    crosses ``node egress link -> [leaf switch -> (spine switch ->) leaf
    switch] -> node ingress link``, and every one of those is a serialising
    resource that other nodes' traffic also wants.  Switch contention is
    reported separately from serialisation because the cluster contract in
    ADR-003 section 3.3 lists them as separate obligations.
    """

    def __init__(self, params: ClusterFabricParams) -> None:
        super().__init__(
            packet_bytes=params.packet_bytes,
            header_bytes=params.packet_header_bytes,
            credits=params.credits,
            credit_return_cycles=params.credit_return_cycles,
            retry_interval_packets=params.retry_interval_packets,
            retry_cycles=params.retry_cycles,
            endpoint_latency_cycles=params.endpoint_latency_cycles,
        )
        self.params = params
        self.topology_class = TopologyClass.CLUSTER_32
        rate = params.link_bytes_per_cycle * params.links_per_node
        self._egress = [
            _Port(f"node{n}.egress", rate) for n in range(params.nodes)
        ]
        self._ingress = [
            _Port(f"node{n}.ingress", rate) for n in range(params.nodes)
        ]
        leaves = max(1, math.ceil(params.nodes / params.switch_radix))
        self._leaf_up = [_Port(f"leaf{i}.up", rate) for i in range(leaves)]
        self._leaf_down = [_Port(f"leaf{i}.down", rate) for i in range(leaves)]
        self._spine = [_Port("spine.0", rate * max(1, leaves // 2))]
        self._leaves = leaves

    def endpoints(self) -> int:
        return self.params.nodes

    def _leaf(self, node: int) -> int:
        return node // self.params.switch_radix

    def route(self, src: int, dst: int) -> _Route:
        params = self.params
        src_leaf = self._leaf(src)
        dst_leaf = self._leaf(dst)
        ports: list[_Port] = [self._egress[src]]
        hops = 1
        switch_latency = params.switch_latency_cycles
        if params.switch_levels == 1 or src_leaf == dst_leaf:
            ports.append(self._leaf_down[dst_leaf])
            hops += 1
            switches = 1
            description = f"node{src}->leaf{src_leaf}->node{dst}"
        else:
            ports.append(self._leaf_up[src_leaf])
            ports.append(self._spine[0])
            ports.append(self._leaf_down[dst_leaf])
            hops += 3
            switches = 3
            description = (
                f"node{src}->leaf{src_leaf}->spine->leaf{dst_leaf}->node{dst}"
            )
        ports.append(self._ingress[dst])
        hops += 1
        latency = hops * params.link_hop_latency_cycles + switches * switch_latency
        return _Route(tuple(ports), latency, hops, description)

    def _barrier_round_cycles(self) -> int:
        return self.params.barrier_round_cycles

    def _all_ports(self) -> list[_Port]:
        return [*self._egress, *self._ingress, *self._leaf_up, *self._leaf_down,
                *self._spine]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "cluster",
            "topology_class": self.topology_class.name,
            "parameters": self.params.to_dict(),
            "leaf_switches": self._leaves,
            "ports": self.port_report(),
        }


# ---------------------------------------------------------------------------
# Wafer-scale logical device
# ---------------------------------------------------------------------------
class WaferFabric(_FabricBase):
    """The on-wafer fabric of the wafer-scale logical accelerator.

    Physical realisation: a 2-D mesh of tiles.  A hop inside a reticle uses the
    ordinary tile link; a hop that crosses a reticle boundary uses the *stitch*
    class, which has its own (lower) bandwidth and (higher) latency because it
    crosses a scribe line.  Routing is dimension-ordered (X then Y), which is
    deterministic and therefore both reproducible and deadlock-free on a mesh
    with the ordinary XY turn restriction -- the property ADR-003 section 3.3
    demands as "deadlock freedom, deterministic routing/ordering where
    architecturally visible".

    Global barriers are hierarchical (tile -> reticle -> wafer and back) so that
    their cost is bounded by ``2 * log2(tiles)`` rounds rather than by the tile
    count, and is never zero.
    """

    def __init__(self, params: WaferFabricParams) -> None:
        super().__init__(
            packet_bytes=params.packet_bytes,
            header_bytes=params.packet_header_bytes,
            credits=params.credits,
            credit_return_cycles=params.credit_return_cycles,
            retry_interval_packets=1 << 30,  # on-wafer links do not retry
            retry_cycles=1,
            endpoint_latency_cycles=params.endpoint_latency_cycles,
        )
        self.params = params
        self.topology_class = TopologyClass.WAFER_LOGICAL_DEVICE
        self.rows = params.reticle_rows * params.tile_rows
        self.cols = params.reticle_cols * params.tile_cols
        self._links: dict[tuple[int, int], _Port] = {}

    def endpoints(self) -> int:
        return self.rows * self.cols

    def coordinate(self, tile: int) -> tuple[int, int]:
        return divmod(tile, self.cols)

    def reticle_of(self, tile: int) -> tuple[int, int]:
        row, col = self.coordinate(tile)
        return row // self.params.tile_rows, col // self.params.tile_cols

    def _link(self, source: int, target: int) -> _Port:
        key = (source, target)
        port = self._links.get(key)
        if port is None:
            stitched = self.reticle_of(source) != self.reticle_of(target)
            rate = (
                self.params.stitch_bytes_per_cycle
                if stitched
                else self.params.tile_link_bytes_per_cycle
            )
            kind = "stitch" if stitched else "tile"
            port = _Port(f"{kind}:{source}->{target}", rate)
            self._links[key] = port
        return port

    def route(self, src: int, dst: int) -> _Route:
        params = self.params
        src_row, src_col = self.coordinate(src)
        dst_row, dst_col = self.coordinate(dst)
        ports: list[_Port] = []
        latency = 0
        hops = 0
        row, col = src_row, src_col
        # Dimension-ordered: all of X first, then all of Y.
        while col != dst_col:
            step = 1 if dst_col > col else -1
            source = row * self.cols + col
            col += step
            target = row * self.cols + col
            ports.append(self._link(source, target))
            stitched = self.reticle_of(source) != self.reticle_of(target)
            latency += (
                params.stitch_hop_cycles if stitched else params.tile_hop_cycles
            ) + params.router_latency_cycles
            hops += 1
        while row != dst_row:
            step = 1 if dst_row > row else -1
            source = row * self.cols + col
            row += step
            target = row * self.cols + col
            ports.append(self._link(source, target))
            stitched = self.reticle_of(source) != self.reticle_of(target)
            latency += (
                params.stitch_hop_cycles if stitched else params.tile_hop_cycles
            ) + params.router_latency_cycles
            hops += 1
        return _Route(
            tuple(ports),
            latency,
            hops,
            f"tile{src}({src_row},{src_col})->tile{dst}({dst_row},{dst_col}) XY",
        )

    def _barrier_round_cycles(self) -> int:
        return self.params.barrier_level_cycles

    def barrier(
        self, participants: Sequence[int], *, start_cycle: int = 0
    ) -> FabricTiming:
        """Hierarchical, bounded on-wafer barrier: tile -> reticle -> wafer.

        The dissemination barrier the base class uses is ``O(P)`` messages per
        round, which is the wrong physical structure on a wafer: the on-wafer
        service is a reduction tree.  The cost is therefore ``2 * ceil(log2 P)``
        tree levels of real routed messages, never zero and never unbounded.
        """
        members = list(dict.fromkeys(int(p) for p in participants))
        count = len(members)
        if count == 0:
            raise FabricError("a barrier needs at least one participant")
        total = FabricTiming(
            operation="barrier",
            start_cycle=start_cycle,
            end_cycle=start_cycle,
            participants=count,
            algorithm="hierarchical_tree",
        )
        levels = max(1, math.ceil(math.log2(count))) if count > 1 else 1
        cursor = start_cycle
        # Up: children report to parents.  Down: the root releases them.
        for phase in ("up", "down"):
            for level in range(levels):
                stride = 1 << level
                round_end = cursor
                for index in range(0, count, stride * 2):
                    partner = index + stride
                    if partner >= count:
                        continue
                    a, b = (partner, index) if phase == "up" else (index, partner)
                    step = self.unicast(
                        members[a], members[b], self.header_bytes,
                        start_cycle=cursor, operation="barrier",
                    )
                    total.merge(step)
                    round_end = max(round_end, step.end_cycle)
                cursor = round_end + self.params.barrier_level_cycles
                total.steps += 1
        total.start_cycle = start_cycle
        total.end_cycle = max(cursor, start_cycle + self.endpoint_latency_cycles)
        return total

    def _all_ports(self) -> list[_Port]:
        return [self._links[key] for key in sorted(self._links)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "wafer",
            "topology_class": self.topology_class.name,
            "parameters": self.params.to_dict(),
            "tile_rows": self.rows,
            "tile_cols": self.cols,
            "instantiated_links": len(self._links),
            "ports": self.port_report(),
        }


# ---------------------------------------------------------------------------
# Construction and invariants
# ---------------------------------------------------------------------------
def build_fabric(machine: MachineModel, topology_class: int):
    """Return the fabric for ``topology_class``, or ``None`` for a single chip."""
    topology = TopologyClass(int(topology_class))
    if topology is TopologyClass.CLUSTER_32:
        return ClusterFabric(machine.cluster_fabric())
    if topology is TopologyClass.WAFER_LOGICAL_DEVICE:
        return WaferFabric(machine.wafer_fabric())
    return None


def assert_no_zero_latency_global_operations(fabric: _FabricBase) -> dict[str, Any]:
    """Check ADR-003 section 9: no collective or barrier may be zero-latency.

    This is an executable check rather than a comment.  It probes the fabric
    with the smallest legal global operations -- a two-participant barrier, a
    zero-byte all-reduce -- on a scratch copy of the fabric state, and asserts
    that each still costs cycles.
    """
    endpoints = fabric.endpoints()
    probes: dict[str, int] = {}
    members = list(range(min(endpoints, 4)))
    if len(members) < 2:
        members = [0, 0]
    saved = [(p, p.free_at, p.busy_cycles, p.contention_cycles) for p in fabric._all_ports()]
    try:
        probes["barrier_cycles"] = fabric.barrier(members).cycles
        probes["zero_byte_all_reduce_cycles"] = fabric.collective(
            int(CollectiveOp.SUM), members, 0
        ).cycles
        probes["one_byte_broadcast_cycles"] = fabric.collective(
            int(CollectiveOp.BROADCAST), members, 1
        ).cycles
    finally:
        for port, free_at, busy, contention in saved:
            port.free_at = free_at
            port.busy_cycles = busy
            port.contention_cycles = contention
    violations = sorted(name for name, cycles in probes.items() if cycles <= 0)
    return {
        "checked": sorted(probes),
        "probe_cycles": dict(sorted(probes.items())),
        "violations": violations,
        "proved": not violations,
        "rule": (
            "ADR-003 section 9: neither simulator may model a global barrier or "
            "collective as zero-latency"
        ),
    }
