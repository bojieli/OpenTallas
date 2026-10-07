#!/usr/bin/env python3
"""Geometry and finite-flow sizing prerequisite; never emits a timing view.

Rectilinear paths avoid inflated macro interiors. The caller supplies endpoints
outside their macros. Inflation must include the actual slice half dimensions
and required clearance. Paths are centre lines, not a placement or DRC proof.
"""
from __future__ import annotations
import bisect
import heapq
import math


def channel_path(start, end, boxes, outline, clearance_um):
    """Shortest Manhattan path on the obstacle-edge coordinate grid, or fail.

    A positive clearance makes touching an inflated edge legal. All rectangles
    describe physical obstructions, including already reserved station boxes.
    Endpoint interiors are never exempted: callers must expose legal portals.
    """
    if clearance_um <= 0:
        raise ValueError('clearance_um must include positive station clearance')
    w, h = outline
    c = clearance_um
    obs = [(x0-c, y0-c, x1+c, y1+c) for x0, y0, x1, y1 in boxes]
    def blocked_point(p):
        x, y = p
        return not (c <= x <= w-c and c <= y <= h-c) or any(
            x0 < x < x1 and y0 < y < y1 for x0,y0,x1,y1 in obs)
    if blocked_point(start) or blocked_point(end):
        raise ValueError('endpoint has no legal station centre at supplied portal')
    xs = sorted({start[0], end[0], c, w-c} |
                {x for b in obs for x in (b[0], b[2]) if c <= x <= w-c})
    ys = sorted({start[1], end[1], c, h-c} |
                {y for b in obs for y in (b[1], b[3]) if c <= y <= h-c})
    # Row/column lists avoid scanning every macro for every A* edge.
    rows = [[(x0,x1) for x0,y0,x1,y1 in obs if y0 < y < y1] for y in ys]
    cols = [[(y0,y1) for x0,y0,x1,y1 in obs if x0 < x < x1] for x in xs]
    source = (bisect.bisect_left(xs,start[0]), bisect.bisect_left(ys,start[1]))
    target = (bisect.bisect_left(xs,end[0]), bisect.bisect_left(ys,end[1]))
    costs, prev = {source:0.0}, {}
    todo = [(abs(start[0]-end[0])+abs(start[1]-end[1]), 0.0, source)]
    while todo:
        _, cost, node = heapq.heappop(todo)
        if cost != costs[node]:
            continue
        if node == target:
            points = []
            while True:
                points.append((xs[node[0]],ys[node[1]]))
                if node == source:
                    break
                node = prev[node]
            points.reverse()
            compact = []
            for point in points:
                if len(compact)>1 and ((compact[-2][0]==compact[-1][0]==point[0]) or
                                      (compact[-2][1]==compact[-1][1]==point[1])):
                    compact.pop()
                compact.append(point)
            return compact
        i,j = node
        for ni,nj in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
            if not (0 <= ni < len(xs) and 0 <= nj < len(ys)):
                continue
            lo,hi = sorted((xs[i],xs[ni]) if ni!=i else (ys[j],ys[nj]))
            intervals = rows[j] if ni!=i else cols[i]
            if any(a < hi and lo < b for a,b in intervals):
                continue
            nxt=(ni,nj)
            nc=cost+hi-lo
            if nc < costs.get(nxt,math.inf):
                costs[nxt],prev[nxt]=nc,node
                heuristic=abs(xs[ni]-end[0])+abs(ys[nj]-end[1])
                heapq.heappush(todo,(nc+heuristic,nc,nxt))
    raise ValueError('no obstacle-free channel path; change floorplan')


def size_chain(*, path, data_bits, slice_bits, slice_area_um2,
               slice_width_um, slice_height_um, channel_tracks,
               period_ps, reverse_hops, consumer_cycles, transactions,
               max_segment_um=300.0, endpoint_max_um=100.0):
    """Price a candidate before RTL. All cycles use the supplied same-clock domain.

    Pin-abutting first/last registers are required. The path joins their centres;
    actual per-bit pin-to-station reach remains a separate qualification gate.
    Credit return represents one consumed beat; depth covers its entire flight
    plus one beat at the capture boundary. No combinational ready chain assumed.
    """
    if len(path)<2 or any(v<=0 for v in (data_bits,slice_bits,slice_area_um2,
            slice_width_um,slice_height_um,channel_tracks,period_ps,max_segment_um,
            endpoint_max_um)) or any(v<0 for v in (reverse_hops,consumer_cycles,transactions)):
        raise ValueError('invalid chain geometry or resource dimensions')
    segments=[]
    for a,b in zip(path,path[1:]):
        if a[0]!=b[0] and a[1]!=b[1]:
            raise ValueError('channel path must be rectilinear')
        segments.append(abs(a[0]-b[0])+abs(a[1]-b[1]))
    # Keep a register at each turn: straight-line sampling cannot cut a corner.
    links=sum(math.ceil(s/max_segment_um) for s in segments)
    stations=links+1
    slices=math.ceil(data_bits/slice_bits)
    depth=stations+reverse_hops+consumer_cycles+1
    # One valid per independently captured slice; one credit-return bit per beat.
    boundary_bits=data_bits+slices+1
    return dict(schema='opentallas.hbm_relay_chain_model.v1', default_off=True,
        status='sized-candidate-not-physical-or-protocol-qualified', MACs_per_cycle=0,
        compute_intensity=0, memory_bytes_per_cycle=0,
        boundary_bits_per_cycle=boundary_bits, data_bytes_per_cycle=data_bits/8,
        slices_per_station=slices, station_count=stations, replica_count=stations*slices,
        lane_padding_bits=slices*slice_bits-data_bits,
        required_tracks=boundary_bits, channel_tracks=channel_tracks,
        channel_capacity_fit=boundary_bits<=channel_tracks,
        station_area_um2=stations*slices*slice_area_um2,
        station_slice_shape_um=[slice_width_um,slice_height_um],
        path_length_um=sum(segments), max_segment_design_um=max_segment_um,
        endpoint_max_design_um=endpoint_max_um,
        latency_cycles=stations, latency_ps=stations*period_ps,
        token_latency_ps=transactions*stations*period_ps,
        credit_round_trip_cycles=stations+reverse_hops+consumer_cycles,
        required_receive_beats=depth, receive_storage_bits=depth*data_bits,
        fanout_per_credit_counter=slices, mux_inputs_per_receive_slice=depth,
        demux_outputs_per_receive_slice=depth,
        required_gates=['actual per-bit endpoint reach <= endpoint_max_design_um',
            'all placed slice boxes legal with reserved clock/reset/PDN channels',
            'source-pinned same-interface routed SS/FF station views',
            'implemented valid/credit/identity/reset protocol exactness and negative control',
            'real clock-domain and original-sink reference binding',
            'per-path token traversal counts composed in system model',
            'receive FIFO area, routing, and SS/FF qualification'])
