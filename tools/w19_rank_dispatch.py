"""Default-off host dispatch on accepted256B baseline descriptors for the model-sized V4.1 GPU rank layout.

This extends the existing busiest-SM ceil partition to clipped contiguous SM
chunks. It does not implement router arithmetic, runtime hardware, or collectives.
Each HBM stack is its existing floorplan quadrant, not a new transport boundary.
"""
MAX_PAYLOADS = 65535 // 2

OPS = {"w1": (2304, 5120), "w3": (2304, 5120), "w2": (5120, 2304)}


def rank_layout(rank, quadrants, *, base_line=17):
    if type(rank) is not int or not 0 <= rank < 96:
        raise ValueError("V4.1 rank must be in [0,96)")
    if type(base_line) is not int or base_line < 0:
        raise ValueError("Invalid HBM line base")
    groups = {int(q): members for q, members in quadrants.items()}
    if sorted(groups) != [0, 1, 2, 3] or any(len(x) != 8 for x in groups.values()):
        raise ValueError("Require four existing eight-SM stack quadrants")
    if sorted(sm for members in groups.values() for sm in members) != list(range(32)):
        raise ValueError("Each actual SM must have exactly one stack owner")
    stacks = {}
    for stack, members in groups.items():
        segments, offset = [], 0
        for sm in members:
            for op, (rows, K) in OPS.items():
                lo, hi = rank * rows // 96, (rank + 1) * rows // 96
                width = (hi - lo + 31) // 32
                a, b = min(hi, lo + sm * width), min(hi, lo + (sm + 1) * width)
                if a == b:
                    continue
                # FP4 has eight block-dot lanes, eight blocks per issue group.
                groups_per_row = ((K // 32 + 7) // 8 + 7) // 8
                payloads = (b - a) * groups_per_row * 8
                lines = payloads * 2
                if not 1 <= payloads <= MAX_PAYLOADS:
                    raise ValueError("Payload descriptor outside existing ports")
                segments.append(dict(rank=rank, stack=stack, sm=sm, operation=op,
                                     rows=[a, b], K=K, payloads=payloads,
                                     cfg_base=base_line, cfg_off=offset, cfg_lines=lines))
                offset += lines
        if offset > 65535 or (base_line + 384 * offset) * 4 > 1 << 24:
            raise ValueError("Expert layout exceeds existing stride/address ports")
        for segment in segments:
            segment["cfg_exp_lines"] = offset
        stacks[stack] = segments
    return stacks


def dispatch(layout, expert_ids, *, stage, producer_ready=False, enable=False):
    """Emit descriptors only at their true producer boundary; no weight math."""
    if not enable:
        raise ValueError("Candidate dispatch is off; explicit enable required")
    ids = list(expert_ids)
    if len(ids) != 6 or any(type(e) is not int or not 0 <= e < 384 for e in ids):
        raise ValueError("Require six physical routed-expert IDs")
    if ids != sorted(set(ids)):
        raise ValueError("Expert IDs must be unique in golden ascending order")
    if stage not in ("input", "output"):
        raise ValueError("Unknown producer stage")
    if stage == "output" and not producer_ready:
        raise ValueError("w2 requires SwiGLU and intermediate-gather completion")
    operations = ("w1", "w3") if stage == "input" else ("w2",)
    by_sm = {(x["sm"], x["operation"]): x for segs in layout.values() for x in segs}
    result = []
    for expert in ids:
        for op in operations:
            for sm in range(32):
                segment = by_sm.get((sm, op))
                if segment is None:
                    continue
                first = (segment["cfg_base"] + expert * segment["cfg_exp_lines"] + segment["cfg_off"]) * 4
                result.append(dict(segment, expert_id=expert, first_sector=first,
                                   sector_count=segment["cfg_lines"] * 4))
    return result
